import pandas as pd
import math

class Oper:
    def __init__(self, id, eqtype, fdt, tt):
        self.id = id
        self.eptype = eqtype
        self.fdt = fdt
        self.tt = tt
        self.next = None
        self.switchDur = 0
        self.switchLots = set()
        self.waitLots = set()
        self.runLots = set()

        if (eqtype == 'MSG'):
            self.switchDur = 5 * 60
        elif (eqtype == 'PHL'):
            self.switchDur = 20 * 60
        elif (eqtype == 'CVD'):
            self.switchDur = 360 * 60
        elif (eqtype == 'DRY'):
            self.switchDur = 60 * 60
        elif (eqtype == 'WET'):
            self.switchDur = 10 * 60
        elif (eqtype == 'STR'):
            self.switchDur = 10 * 60

class EQ:
    def __init__(self, id):
        self.id = id
        self.status = 0
        self.oper = None
        self.nowProductId = 0
        self.availOper = {}
        self.availProduct = {}
        self.lot = None
        self.workEndTime = -1

class Lot:
    def __init__(self, id, productId, ver, oper, status, glassQty, stayTime, level):
        self.id = id
        self.productId = productId
        self.ver = ver
        self.status = status
        self.oper = oper
        self.glassQty = glassQty
        self.stayTime = stayTime # 单位 s
        self.level = level
        self.eq = None
        self.switchEndTime = -1

class Solution:

    def __init__(self):
        self.opers = {}
        self.eqs = {}
        self.lots = {}
        self.productWait = {}
        return 

    def init(self):
        self.readFlow()
        self.readEP()
        self.readWIP()

        return 

    def readFlow(self):
        df = pd.read_csv("Flow.csv")
        nrows = df.shape[0]
        beforeLot = None
        for i in range(0, nrows):
            row = df.iloc[i, :]
            oper = Oper(row[0], row[1], row[2], row[3])
            if beforeLot != None:
                beforeLot.next = oper
            self.opers[row[0]] = oper
            beforeLot = oper

        return
    
    def readEP(self):

        eqtypes = ['MSP', 'ITO', 'PHL', 'CVD', 'DRY', 'WET', 'STR', 'OVN']
        self.eqs = {}
        for eqtype in eqtypes:
            filename = "eq_" + eqtype + ".csv"
            df = pd.read_csv(filename)
            nrows = df.shape[0]
            ncols = df.shape[1]
            for i in range(2, ncols):
                id = df.columns[i]
                self.eqs[id] = EQ(id)
                
                for j in range(0, nrows):
                    if df.iloc[j, i] == 'Y':
                        operId = df.iloc[j, 0]
                        productId = df.iloc[j, 1]
                        if operId not in self.eqs[id].availOper:
                            self.eqs[id].availOper[operId] = []
                        
                        if productId not in self.eqs[id].availProduct:
                            self.eqs[id].availProduct[productId] = []
                        
                        self.eqs[id].availOper[operId].append(productId)
                        self.eqs[id].availProduct[productId].append(operId)

        return
    
    def readWIP(self):
        df = pd.read_csv("wip.csv")
        nrows = df.shape[0]
        for i in range(0, nrows):    
            row = df.iloc[i, :]
            ver = None; 
            if type(row[2]) == str:
                ver = row[2] 
            status = 0
            if row[4] == 'RUN':
                status = 1
            oper = self.opers[row[3]]
            stayTime = math.ceil(row[7] * 3600)
            level = 0
            if row[8] == 1:
                level = 1
            
            lot = Lot(row[0], row[1], ver, oper, status, row[6], stayTime, level)

            eqname = row[5]
            if (type(eqname) == str):
                eqname = eqname[2:]
                eq = self.eqs[eqname]
                eq.status = 1
                eq.oper = oper
                eq.nowProductId = row[1]
                eq.lot = lot
                eq.workEndTime = eq.oper.fft + (eq.lot.glassQty - 1) * eq.oper.tt
                lot.eq = eq

            self.lots[row[0]] = lot
        
        return


    def run(self):

        # EQ 初始放置策略
        for eq in self.eqs.values():
            if eq.oper == None:
                eq.oper = eq.availOpers.keys()[0]
                eq.productId = eq.availOpers.values()[0]

        totalTime = 24 * 60 * 60
        for t in range(0, totalTime):
            # 查看站点传送带上 Lot 是否运达
            # 若运达，转移 Lot 到等待链上
            for oper in self.opers.values():
                toremove = set()
                for lot in oper.switchLots:
                    if lot.switchEndTime <= t:
                        lot.switchEndTime = -1
                        toremove.add(lot)
                oper.switchLots.symmetric_difference_update(toremove)
                oper.waitLots.symmetric_difference_update(toremove)
                        
            # 查看机台是否都工作完
            # 若工作完，置机台为空闲状态
            # 转移 Lot 出当前站点，track out，并 track in 进入下一个站台
            # 并视察是否进入传送链
            for eq in self.eqs.values():
                if eq.status == 1 and eq.workEndTime <= t:
                    lot = eq.lot
                    eq.lot = None
                    eq.status = 0
                    eq.workEndTime = -1

                    lot.eq = None
                    lot.status = 0
                    lot.oper = lot.oper.next
                    
                    # 产品完成
                    if lot.oper == None:
                        continue
                    elif (lot.oper.switchDur > 0):
                        lot.switchEndTime = t + lot.oper.switchDur
                        lot.oper.switchLots.add(lot)
                    else:
                        lot.switchEndTime = -1
                        lot.oper.waitLots.add(lot)
                        
            # EQ 工作策略
            # 先考虑前后处理同样的 productId
            # 在考虑其他种类的 productId
            # 可随意换站点
                        
            # 处理时
            # 在考虑先处理等级 1
            # 再考虑处理时间长的

            # 换类型处理时
            # 类型选择现在机台能处理的类型中，优先级较高，等待数量最长的产品类型
            for eq in self.eqs.values():
                if (eq.status == 0):
                    maxTime = -1
                    targetLevel = 0
                    targetLot = None
                    availOpers = eq.availProduct[eq.nowProductId]

                    for operId in availOpers:
                        for lot in self.opers[operId].lots:
                            if (lot.status == 0 and lot.productId == eq.nowProductId and targetLevel <= lot.level):
                                targetLevel = lot.level
                                if (lot.stayTime > maxTime):
                                    maxTime = lot.stayTime
                                    targetLot = lot

                    if (targetLot != None):
                        targetLot.status = 1
                        targetLot.eq = eq
                        targetLot.stayTime = 0

                        eq.lot = targetLot
                        eq.oper = targetLot.oper
                        eq.workEndTime = t + eq.oper.fft + (eq.lot.glassQty - 1) * eq.oper.tt
                        
                        return

        
        return