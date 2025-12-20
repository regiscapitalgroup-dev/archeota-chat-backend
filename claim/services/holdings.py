from decimal import Decimal
from django.db import transaction
from django.db.models import Q
from claim.models import ClaimActionTransaction, ActionsHoldings
from users.models import Company

class HoldingService():
    def __init__(self, user):
        self.user = user
        self.buy_activities = ['BUY', 'INCOME']
    
    @transaction.atomic
    def __get_first_buy(self, symbol) -> ActionsHoldings | None:
        qs = ActionsHoldings.objects.filter(
            user=self.user, 
            symbol=str(symbol).strip(),
            useless=False,
        )
        q_filter = Q()
        for act in self.buy_activities:
            if '.*' in act:
                q_filter |= Q(activity__iregex=act)
            else:
                q_filter |= Q(activity__icontains=act)
        return qs.filter(q_filter).order_by('lot_number').first()
    
    @transaction.atomic
    def __generate_name(self, symbol) -> tuple[int, str]:
        qs = ActionsHoldings.objects.filter(
            user=self.user, 
            symbol=str(symbol).strip(),
        )
        q_filter = Q()
        for act in self.buy_activities:
            if '.*' in act:
                q_filter |= Q(activity__iregex=act)
            else:
                q_filter |= Q(activity__icontains=act)
        lot_number = 1
        count = qs.filter(q_filter).order_by('-lot_number').first()
        if count:
            lot_number = count.lot_number+1
        return (lot_number, f"LOT{lot_number:05d}")

    @transaction.atomic
    def buy_activity(self, claim: ClaimActionTransaction):
        lot_number, name = self.__generate_name(claim.symbol)
        holding = ActionsHoldings(
            lot_number=lot_number,
            name=name,
            start_date=claim.trade_date,
            symbol=claim.symbol,
            quantity=claim.quantity,
            amount=claim.amount,
            activity=claim.activity,
            cost_per_stock=claim.cost_per_stock,
            user=self.user,
            company=self.user.profile.company
            # transaction=claim
        )
        holding.save()

    @transaction.atomic
    def sell_activity(self, claim: ClaimActionTransaction):
        first_buy = self.__get_first_buy(claim.symbol)
        if first_buy is None:
            ## in theory, it never pass here
            raise Exception(f"There are not enough funds to apply the discount. {claim.activity} on {claim.trade_date}")
        selling = ActionsHoldings(
            lot_number=first_buy.lot_number,
            end_date=claim.trade_date,
            symbol=claim.symbol,
            quantity=claim.quantity,
            amount=claim.amount,
            activity=claim.activity,
            cost_per_stock=claim.cost_per_stock,
            user=self.user,
            company=self.user.profile.company
            # transaction=claim
        )
        selling.save()
        quantity_left = first_buy.quantity - selling.quantity
        if(quantity_left < 0):
            while quantity_left < 0:
                lot_finished = ActionsHoldings(
                    lot_number=first_buy.lot_number,
                    name=f"LOT{first_buy.lot_number:05d}_FINISHED",
                    start_date=first_buy.start_date,
                    end_date=selling.end_date,
                    activity=selling.activity,
                    symbol=selling.symbol,
                    quantity=first_buy.quantity,
                    amount=(first_buy.cost_per_stock*Decimal(selling.quantity)),
                    cost_per_stock=first_buy.cost_per_stock,
                    user=self.user,
                    company=self.user.profile.company
                    # transaction=first_buy.transaction
                )
                first_buy.useless = True
                lot_finished.save()
                first_buy.save()
                first_buy = self.__get_first_buy(claim.symbol)
                if first_buy is None:
                    ## here the sell down to negative and there is not any buy to rest
                    raise Exception(f"There are not enough funds to apply the discount. {claim.activity} on {claim.trade_date}")

                if first_buy.quantity > abs(quantity_left):
                    discount = ActionsHoldings(
                        lot_number=first_buy.lot_number,
                        name=f"LOT{first_buy.lot_number:05d}_DISCOUNTED",
                        start_date=first_buy.start_date,
                        end_date=selling.end_date,
                        symbol=selling.symbol,
                        activity=selling.activity,
                        quantity=abs(quantity_left),
                        amount=(first_buy.cost_per_stock*Decimal(abs(quantity_left))),
                        cost_per_stock=first_buy.cost_per_stock,
                        user=self.user,
                        company=self.user.profile.company
                        # transaction=first_buy.transaction
                    )
                    discount.save()

                quantity_left = first_buy.quantity - abs(quantity_left)
            if first_buy is None:
                return
            if quantity_left == 0:
                lot_finished = ActionsHoldings(
                    lot_number=first_buy.lot_number,
                    name=f"LOT{first_buy.lot_number:05d}_FINISHED",
                    start_date=first_buy.start_date,
                    end_date=selling.end_date,
                    activity=selling.activity,
                    symbol=selling.symbol,
                    quantity=first_buy.quantity,
                    amount=(first_buy.cost_per_stock*Decimal(first_buy.quantity)),
                    cost_per_stock=first_buy.cost_per_stock,
                    user=self.user,
                    company=self.user.profile.company
                    # transaction=first_buy.transaction
                )
                first_buy.useless = True
                first_buy.save()
                lot_finished.save()
            else:
                new_buy = ActionsHoldings(
                    lot_number=first_buy.lot_number,
                    name=f"LOT{first_buy.lot_number:05d}",
                    start_date=first_buy.start_date,
                    symbol=selling.symbol,
                    activity=first_buy.activity,
                    quantity=quantity_left,
                    amount=(first_buy.cost_per_stock*Decimal(quantity_left)),
                    cost_per_stock=first_buy.cost_per_stock,
                    user=self.user,
                    company=self.user.profile.company
                    # transaction=first_buy.transaction
                )
                first_buy.useless = True
                first_buy.save()
                
                new_buy.save()
        else:
            if quantity_left == 0:
                lot_finished = ActionsHoldings(
                    lot_number=first_buy.lot_number,
                    name=f"LOT{first_buy.lot_number:05d}_FINISHED",
                    start_date=first_buy.start_date,
                    end_date=selling.end_date,
                    activity=selling.activity,
                    symbol=selling.symbol,
                    quantity=first_buy.quantity,
                    amount=(first_buy.cost_per_stock*Decimal(first_buy.quantity)),
                    cost_per_stock=first_buy.cost_per_stock,
                    user=self.user,
                    company=self.user.profile.company
                    # transaction=first_buy.transaction
                )
                first_buy.useless = True
                first_buy.save()
                lot_finished.save()
            else:
                discount = ActionsHoldings(
                    lot_number=first_buy.lot_number,
                    name=f"LOT{first_buy.lot_number:05d}_DISCOUNTED",
                    start_date=first_buy.start_date,
                    end_date=selling.end_date,
                    symbol=selling.symbol,
                    activity=selling.activity,
                    quantity=selling.quantity,
                    amount=(first_buy.cost_per_stock*Decimal(selling.quantity)),
                    cost_per_stock=first_buy.cost_per_stock,
                    user=self.user,
                    company=self.user.profile.company
                    # transaction=first_buy.transaction
                )
                new_buy = ActionsHoldings(
                    lot_number=first_buy.lot_number,
                    name=f"LOT{first_buy.lot_number:05d}",
                    start_date=first_buy.start_date,
                    symbol=selling.symbol,
                    activity=first_buy.activity,
                    quantity=quantity_left,
                    amount=(first_buy.cost_per_stock*Decimal(quantity_left)),
                    cost_per_stock=first_buy.cost_per_stock,
                    user=self.user,
                    company=self.user.profile.company
                    # transaction=first_buy.transaction
                )
                first_buy.useless = True
                first_buy.save()
                discount.save()
                new_buy.save()
    
    @transaction.atomic
    def company_holdings(self, company: Company, symbol: str, start_date: str, end_date: str):
        return (
            ActionsHoldings.objects
            .filter(
                company=company,
                symbol=symbol,
                useless=False
            )
            .filter(
                Q(
                    activity='Buy',
                    start_date__lte=end_date
                ) & (
                    Q(end_date__gte=start_date) | Q(end_date__isnull=True)
                )
                |
                Q(
                    activity='Sell',
                    start_date__lte=end_date,
                    end_date__gte=start_date
                )
            )
            .order_by('start_date', 'id')
        )

        

    