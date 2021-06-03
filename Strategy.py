# 用CCI指數在超賣區買入 15%停損
class Strategy():
    # option setting needed
    def __setitem__(self, key, value):
        self.options[key] = value

    # option setting needed
    def __getitem__(self, key):
        return self.options.get(key, '')

    def __init__(self):
        # strategy property
        self.subscribedBooks = {
            'Binance': {
                'pairs': ['ADA-USDT'],
            },
        }
        self.period = 15 * 60
        self.options = {}

        # user defined class attribute
        self.last_type = 'sell'
        self.last_cross_status = None
        self.close_price_trace = np.array([])
        self.ma_long = 250
        self.ma_short = 20
        self.ma_250=0
        self.ma_20=0
        self.UP = 1
        self.DOWN = 2

        self.high_price_trace = np.array([])
        self.low_price_trace = np.array([])

        self.cost_price = 0
        self.buy_under_long_ma = False

    def on_order_state_change(self,  order):
        Log("on order state change message: " + str(order) + " order price: " + str(order["price"]))

    def get_current_ma(self):
        self.ma_20 = talib.SMA(self.close_price_trace, self.ma_short)[-1]
        self.ma_250 = talib.SMA(self.close_price_trace, self.ma_long)[-1]

    def update_current_cci(self , high , low , close):

        cci_now = talib.CCI(high, low, close, timeperiod=20)
        return cci_now

    def check_cci_signal(self,cci_now):

        status = 0
        pre_cci = cci_now[-3]
        for cci in cci_now[-2:]:
            if pre_cci < -100 :
                if cci > -100:
                    #從-100往上衝破 第一次
                    status = 1
            elif (99.9> pre_cci >= -100):
                # if cci < -100:
                #     # 從-100 往下衝破 賣出
                #     status = 4 
                if cci > -100 and status == 1:
                    #從100往上衝破且沒掉回去 買入
                    status = 2
            elif (100 <= pre_cci):
                if cci <= 100:
                    status = 3
            elif pre_cci <= 100:
                if cci <= 100 and status == 3 :
                    status = 4
            pre_cci = cci
        return status

    def take_profit(self,close_price):
        if self.cost_price*1.33 <= close_price:
            return 1
        return 0

    # called every self.period
    def trade(self, information):
        exchange = list(information['candles'])[0]
        pair = list(information['candles'][exchange])[0]
        target_currency = pair.split('-')[0]  #ETH
        base_currency = pair.split('-')[1]  #USDT
        base_currency_amount = self['assets'][exchange][base_currency] 
        target_currency_amount = self['assets'][exchange][target_currency] 
        # add latest price into trace
        close_price = information['candles'][exchange][pair][0]['close']
        high_price = information['candles'][exchange][pair][0]['high']
        low_price = information['candles'][exchange][pair][0]['low']
        self.close_price_trace = np.append(self.close_price_trace, [float(close_price)])
        self.high_price_trace = np.append(self.high_price_trace, [float(high_price)])
        self.low_price_trace = np.append(self.low_price_trace, [float(low_price)])
        self.get_current_ma()

        # cal cci 
        cci_now = self.update_current_cci(self.high_price_trace,self.low_price_trace,self.close_price_trace)
        # Log('cci now is' + cci_now)
        # Log('cci updated!!' + cci_now)
        # only keep max length of ma_long count elements
        self.close_price_trace = self.close_price_trace[-self.ma_long:]
        self.high_price_trace = self.high_price_trace[-self.ma_long:]
        self.low_price_trace = self.high_price_trace[-self.ma_long:]
        cci_now = cci_now[-self.ma_long:]

        if np.size(cci_now) <20:
            return []

        if np.size(self.close_price_trace) <20:
            return []

                #take profit
        if self.take_profit(close_price) == 1:
            if self.last_type == 'buy':
                self.last_type = 'sell'
                return [
                {
                    'exchange': exchange,
                    'amount': -target_currency_amount,
                    'price': -1,
                    'type': 'MARKET',
                    'pair': pair,
                }
            ]


        #15% stop loss
        if self.cost_price != 0:
            if self.last_type == 'buy' and close_price <= self.cost_price * 0.85 :
                self.last_type = 'sell'
                return [
                {
                    'exchange': exchange,
                    'amount': -target_currency_amount,
                    'price': -1,
                    'type': 'MARKET',
                    'pair': pair,
                }
            ]
        
        # Check cci signal
        cci_signal = self.check_cci_signal(cci_now)
        if self.last_type == 'sell' and cci_signal == 2:

            self.last_type = 'buy'
            ready_to_buy_amount = base_currency_amount/close_price
            ready_to_buy_amount*0.98
            self.cost_price = close_price
            if close_price < self.ma_250:
                self.buy_under_long_ma = True
            return [
                {
                    'exchange': exchange,
                    'amount': ready_to_buy_amount,
                    'price': close_price,
                    'type': 'LIMIT',
                    'pair': pair,
                }
            ]
        elif self.last_type == 'buy' and cci_signal == 4:
            self.last_type = 'sell'
            return [
                {
                    'exchange': exchange,
                    'amount': -target_currency_amount,
                    'price': -1,
                    'type': 'MARKET',
                    'pair': pair,
                }
            ]


        return []
