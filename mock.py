import json,math,random
IDS=['bitcoin','ethereum','solana','litecoin','ripple','binancecoin','dogecoin','cardano','tron','avalanche-2','chainlink','the-open-network','sui','stellar','bitcoin-cash','polkadot']
BASE={'bitcoin':80000,'ethereum':3200,'solana':160,'litecoin':95,'ripple':2.1,'binancecoin':640,'dogecoin':0.19,'cardano':0.62,'tron':0.27,'avalanche-2':31,'chainlink':17.5,'the-open-network':3.4,'sui':3.8,'stellar':0.31,'bitcoin-cash':480,'polkadot':4.9}
def payload(seed=1,drop=None):
    r=random.Random(seed);out=[];now='2026-10-11T14:00:00.000Z'
    for i,id in enumerate(IDS):
        if drop and id in drop:continue
        p=BASE[id];sp=[];x=p*0.97
        for k in range(168):
            x*=1+(r.random()-.48)*.006;sp.append(round(x,6))
        cur=sp[-1];last24=sp[-25:]
        out.append({'id':id,'symbol':id[:3],'name':id.title(),'current_price':cur,'market_cap':cur*1e7*(20-i),'market_cap_rank':i+1,'total_volume':cur*1e6*(20-i),'high_24h':max(last24),'low_24h':min(last24),'price_change_percentage_24h':(cur/sp[-25]-1)*100,'price_change_percentage_1h_in_currency':(cur/sp[-2]-1)*100,'price_change_percentage_24h_in_currency':(cur/sp[-25]-1)*100,'price_change_percentage_7d_in_currency':(cur/sp[0]-1)*100,'last_updated':now,'sparkline_in_7d':{'price':sp}})
    return out
