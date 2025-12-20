from copy import copy
import datetime
from decimal import Decimal
import decimal
import re
from django.db import transaction
from django.forms import model_to_dict
from claim.models import ClaimActionTransaction
from collections import defaultdict
from django.db.models import Q
from claim.services.holdings import HoldingService

class TransactionService():
    def __init__(self, user, company_profile):
        self.user = user
        self.company_profile = company_profile
        if not self.company_profile:
            self.company_profile = 'No Company'
        self.actions_saved: list[ClaimActionTransaction] = []
        self.buy_activities = ['BUY', 'INCOME']
        self.sell_activities = ['SELL']
        self.holding_svc = HoldingService(self.user)

    def is_buy_activity(self, activity: str) -> bool:
        if activity is None:
            return False
        activity = activity.strip().upper()
        for act in self.buy_activities:
            if '.*' in act:
                return re.search(act, activity) is not None
            else:
                return True if activity in act else False 

    def is_sell_activity(self, activity: str) -> bool:
        if activity is None:
            return False
        return True if activity.strip().upper() in self.sell_activities else False

    @transaction.atomic
    def validate_oldest_buy(self, symbol, activity_row) -> bool:
        qs = (ClaimActionTransaction.objects
                .filter(user=self.user, symbol=symbol))
        q_filter = Q()
        for act in self.buy_activities:
            if '.*' in act:
                q_filter |= Q(activity__iregex=act)
            else:
                q_filter |= Q(activity__icontains=act)
        oldest = qs.filter(q_filter).order_by('trade_date', 'id').first()
        return not ((
            activity_row is None
            or str(activity_row).strip().upper() in self.sell_activities
        ) and not oldest)

    @transaction.atomic
    def insert_objects(self, bulk):
        ClaimActionTransaction.objects.bulk_create(bulk)
        self.actions_saved.extend(bulk)
    
    def create_instance(self, data_for, trade_date, account, account_name, account_type, account_number, activity, description, symbol, quantity, cost_per_stock, amount, notes):
        return ClaimActionTransaction(
            data_for=data_for,
            trade_date=trade_date,
            account=account,
            account_name=account_name,
            account_type=account_type,
            account_number=account_number,
            activity=activity,
            description=description,
            symbol=symbol,
            quantity=quantity,
            cost_per_stock=cost_per_stock,
            amount=amount,
            notes=notes,
            type='Type',
            company=self.company_profile,
            user=self.user,
        )

    def __order_actions(self):
        symbols_ordered: defaultdict[str, list[ClaimActionTransaction]] = defaultdict(list[ClaimActionTransaction])
        # types = []
        # for o in self.actions_saved:
        #     if type(o.symbol) not in types:
        #         types.append(type(o.symbol))
        # print(types)
        self.actions_saved.sort(key=lambda o: (str(o.symbol), o.trade_date))
        for row in self.actions_saved:
            if row.symbol is None or row.trade_date is None:
                continue
            symbols_ordered[row.symbol].append(row)
        return symbols_ordered

    def __group_symbols(self, actions: list[ClaimActionTransaction]) -> list[ClaimActionTransaction]: 
        group_dates = defaultdict(list[ClaimActionTransaction])
        for action in actions:
            group_dates[action.trade_date.date()].append(action)
        # Create summarize
        result: defaultdict[datetime.datetime, list[ClaimActionTransaction]] = defaultdict(list[ClaimActionTransaction])
        for trade_date, claims in group_dates.items():
            groups: defaultdict[tuple[str, Decimal], ClaimActionTransaction] = {}
            for claim in claims:
                if claim.activity is None or claim.cost_per_stock is None:
                    continue
                activity = str(claim.activity).strip().upper()
                cost_per_stock = (claim.cost_per_stock / Decimal('0.01')).to_integral_value() * Decimal('0.001')
                compare_keys = (activity, cost_per_stock)
                if compare_keys not in groups:
                    groups[compare_keys] = self.create_instance(
                        data_for=claim.data_for,
                        trade_date=claim.trade_date,
                        account=claim.account,
                        account_name=claim.account_name,
                        account_type=claim.account_type,
                        account_number=claim.account_number,
                        activity=claim.activity,
                        description=claim.description,
                        symbol=claim.symbol,
                        quantity=claim.quantity,
                        cost_per_stock=claim.cost_per_stock,
                        amount=claim.amount,
                        notes=claim.notes,
                    )
                else:
                    groups[compare_keys].quantity += claim.quantity
                    groups[compare_keys].amount += claim.amount
            
            result[trade_date] = list(groups.values())
        return result

    def __process_group(self, claims_by_dates: defaultdict[datetime.datetime, list[ClaimActionTransaction]]):
        warnings = {}
        for _, claims in claims_by_dates.items():
            for claim in claims:
                try:
                    if self.is_buy_activity(claim.activity):
                        self.holding_svc.buy_activity(claim)
                    elif self.is_sell_activity(claim.activity):
                        self.holding_svc.sell_activity(claim)
                except Exception as e:
                    warnings[claim.symbol] = str(e)
        return warnings
        

    def process_bulk(self):
        warnings = []
        symbol_ordered = self.__order_actions()
        for __symbol, actions in symbol_ordered.items():
            group = self.__group_symbols(actions)
            warns = self.__process_group(group)
            warnings.append(warns)
        self.actions_saved.clear()
        return warnings
