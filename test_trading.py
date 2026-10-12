import json,base64,re,urllib.parse
import os,sys
HERE=os.path.dirname(os.path.abspath(__file__));sys.path.insert(0,HERE)
URL='file://'+os.path.abspath(os.path.join(HERE,'..','public','index.html'))
AUDIT=open(os.path.join(HERE,'audit.js')).read()
from playwright.sync_api import sync_playwright
errs=[];res=[]
def ok(name,cond,extra=''):
    res.append((name,bool(cond)));print(('PASS ' if cond else 'FAIL ')+name+(' | '+str(extra) if extra!='' else ''))
A58='123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
def b58e(b):
    n=int.from_bytes(b,'big');s=''
    while n>0:n,r=divmod(n,58);s=A58[r]+s
    return '1'*(len(b)-len(b.lstrip(b'\0')))+s
def b58d(s):
    n=0
    for ch in s:n=n*58+A58.index(ch)
    b=n.to_bytes((n.bit_length()+7)//8,'big') if n else b''
    return b'\0'*(len(s)-len(s.lstrip('1')))+b
PK=bytes(range(1,33));ADDR=b58e(PK);PK2=bytes(range(40,72));ADDR2=b58e(PK2)
JUP=b58d('JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4')
M={'sol':'So11111111111111111111111111111111111111112','usdc':'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v','usdt':'Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB','jup':'JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN','bonk':'DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263','wif':'EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm'}
DEC={'sol':9,'usdc':6,'usdt':6,'jup':6,'bonk':5,'wif':6,'jitosol':9,'msol':9,'ray':6,'pyth':6}
MINTDEC={v:DEC[k] for k,v in M.items()}
TOKENKEG='TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA'
CUSTOM='7GCihgDB8fe6KNjn2MYtkzZcRjQy3t9GHdC8uHYmW2hr'
def mk_tx(payer=PK,jup=True,nsig=1,req=1,v0=True):
    keys=[payer,bytes([9])*32,(JUP if jup else bytes([5])*32)]
    msg=(b'\x80' if v0 else b'')+bytes([req,0,1])+bytes([len(keys)])+b''.join(keys)+bytes(32)+b'\x00'+(b'\x00' if v0 else b'')
    return bytes([nsig])+bytes(64*nsig)+msg
GOOD=mk_tx()
def mkstate():
    return {'sol':2_500_000_000,'tokens':[{'mint':M['jup'],'amount':'125500001','dec':6},{'mint':M['bonk'],'amount':'987654321','dec':5},{'mint':M['wif'],'amount':'0','dec':6}],'t22':[{'mint':'Zx9mQ2VnYk3Lw7PaRtB5cDeHfJgKm8NsXu6yAbCdEfG','amount':'5000','dec':3}],'rate':0.5,'impact':'0.0012','quotes':[],'swaps':[],'rpc':[],'decimals':dict(MINTDEC),'swapmode':'ok','sigseq':[None,'confirmed'],'rpcfail':False,'rpcabort':False,'jupabort':False,'quotefail':None,'hosts':set(),'sent':[],'quotebad':None,'swaptx':GOOD}
CORS={'access-control-allow-origin':'*','access-control-allow-headers':'*','access-control-allow-methods':'*'}
def jres(route,obj,status=200):route.fulfill(status=status,headers=dict(CORS,**{'content-type':'application/json'}),body=json.dumps(obj) if not isinstance(obj,str) else obj)
def handlers(ST):
    def rpc(route):
        rq=route.request;ST['hosts'].add(urllib.parse.urlparse(rq.url).netloc)
        if rq.method=='OPTIONS':return route.fulfill(status=204,headers=CORS)
        if ST['rpcabort']:return route.abort()
        if ST['rpcfail']:return jres(route,'oops',500)
        b=json.loads(rq.post_data);m,p=b['method'],b['params'];ST['rpc'].append((m,p))
        if m=='getBalance':r={'value':ST['sol']}
        elif m=='getTokenAccountsByOwner':
            lst=ST['tokens'] if p[1]['programId']==TOKENKEG else ST['t22']
            r={'value':[{'pubkey':'x','account':{'data':{'parsed':{'info':{'mint':t['mint'],'tokenAmount':{'amount':t['amount'],'decimals':t['dec']}}}}}} for t in lst]}
        elif m=='getTokenSupply':
            d=ST['decimals'].get(p[0])
            if d is None:return jres(route,{'jsonrpc':'2.0','id':1,'error':{'code':-32602,'message':'Invalid param: not a Token mint'}})
            r={'value':{'amount':'1000','decimals':d}}
        elif m=='getSignatureStatuses':
            s=ST['sigseq'].pop(0) if len(ST['sigseq'])>1 else ST['sigseq'][0]
            r={'value':[None if s is None else ({'err':{'InstructionError':[0,'Custom']},'confirmationStatus':'confirmed'} if s=='failed' else {'err':None,'confirmationStatus':s})]}
        elif m=='sendTransaction':ST['sent'].append(p[0]);r=b58e(bytes([3])*64)
        else:r=None
        jres(route,{'jsonrpc':'2.0','id':1,'result':r})
    def jup(route):
        rq=route.request;ST['hosts'].add(urllib.parse.urlparse(rq.url).netloc)
        if rq.method=='OPTIONS':return route.fulfill(status=204,headers=CORS)
        if ST['jupabort']:return route.abort()
        u=urllib.parse.urlparse(rq.url)
        if u.path.endswith('/quote'):
            q=dict(urllib.parse.parse_qsl(u.query));ST['quotes'].append(q)
            if ST['quotefail']:return jres(route,ST['quotefail'][1],ST['quotefail'][0])
            amt=int(q['amount']);inm,outm=q['inputMint'],q['outputMint'];din,dout=MINTDEC.get(inm,ST['decimals'].get(inm,6)),MINTDEC.get(outm,ST['decimals'].get(outm,6))
            out=int(amt*ST['rate']*10**dout/10**din);slip=int(q['slippageBps'])
            obj={'inputMint':inm,'inAmount':str(amt),'outputMint':outm,'outAmount':str(out),'otherAmountThreshold':str(out*(10000-slip)//10000),'swapMode':'ExactIn','slippageBps':slip,'priceImpactPct':ST['impact'],'routePlan':[{'swapInfo':{'label':'Orca'},'percent':100}],'contextSlot':1}
            if ST['quotebad']:obj.update(ST['quotebad'])
            return jres(route,obj)
        if u.path.endswith('/swap'):
            b=json.loads(rq.post_data);ST['swaps'].append(b);m=ST['swapmode']
            if m=='500':return jres(route,'boom',500)
            if m=='error':return jres(route,{'error':'Simulation failed'},400)
            if m=='nofield':return jres(route,{'ok':1})
            if m=='garbage':return jres(route,{'swapTransaction':'!!!notbase64!!!'})
            return jres(route,{'swapTransaction':base64.b64encode(ST['swaptx']).decode(),'lastValidBlockHeight':1})
        route.abort()
    return rpc,jup
def wallet_js(addr=ADDR,pk=PK,sign=True,send=True,name='MockWallet'):
    feats=[]
    if send:feats.append("'solana:signAndSendTransaction':{version:'1.0.0',signAndSendTransaction:async function(i){C.push('signAndSend');window.__sent={chain:i.chain,addr:i.account.address,tx:Array.from(i.transaction)};if(O.reject)throw new Error('User rejected the request');if(O.delay)await new Promise(r=>setTimeout(r,O.delay));return [{signature:new Uint8Array(64).fill(7)}]}}")
    if sign:feats.append("'solana:signTransaction':{version:'1.0.0',signTransaction:async function(i){C.push('signTransaction');window.__signedIn=Array.from(i.transaction);if(O.reject)throw new Error('User rejected the request');return [{signedTransaction:new Uint8Array(i.transaction)}]}}")
    return """(function(){var C=window.__wc=[],O=window.__wo={};var acct={address:'%s',publicKey:new Uint8Array(%s),chains:['solana:mainnet'],features:[]};var w={name:'%s',version:'1.0.0',icon:'data:image/svg+xml;base64,PHN2Zy8+',chains:['solana:mainnet'],accounts:[],features:{'standard:connect':{version:'1.0.0',connect:async function(){C.push('connect');if(O.noconnect)throw new Error('User rejected the request');w.accounts=[acct];return {accounts:[acct]}}},'standard:disconnect':{version:'1.0.0',disconnect:async function(){C.push('disconnect')}},'standard:events':{version:'1.0.0',on:function(e,cb){window.__emit=cb;return function(){}}},%s}};window.__w=w;function reg(api){api.register(w)}window.addEventListener('wallet-standard:app-ready',function(e){reg(e.detail)});window.dispatchEvent(new CustomEvent('wallet-standard:register-wallet',{detail:reg}))})();"""%(addr,json.dumps(list(pk)),name,','.join(feats))
def page(ST=None,wallet=True,vp=(1360,1000),mobile=False,extra='',wopts=None,routes=True):
    ST=ST if ST is not None else mkstate()
    c=br.new_context(viewport={'width':vp[0],'height':vp[1]},is_mobile=mobile,has_touch=mobile);c.add_init_script("window.__fast=true;"+(wallet_js(**(wopts or {})) if wallet else '')+extra)
    rpc,jup=handlers(ST);c.route('https://api.mainnet-beta.solana.com/**',rpc);c.route('https://lite-api.jup.ag/**',jup);c.route('https://api.coingecko.com/**',lambda r:r.abort())
    pg=c.new_page();pg.on('pageerror',lambda e:errs.append(str(e)));pg.goto(URL);pg.wait_for_timeout(1300);pg.evaluate("document.getElementById('trade').scrollIntoView({behavior:'instant'})");return c,pg,ST
def connect(pg):
    pg.click('[data-wallet=MockWallet]');pg.wait_for_timeout(400)
def setamt(pg,v):
    pg.fill('#lvAmt',v);pg.wait_for_timeout(300)
with sync_playwright() as p:
    br=p.chromium.launch()
    # ================= pure functions
    c,pg,ST=page(wallet=False);E=pg.evaluate
    ok('base58 matches an independent implementation (including leading zero bytes) and round-trips',all(E("__sp.LV.b58enc(new Uint8Array(%s))"%json.dumps(list(v)))==b58e(bytes(v)) and E("Array.from(__sp.LV.b58dec(%r))"%b58e(bytes(v)))==list(v) for v in [PK,PK2,[0,0,1,2,3],[0],[255]*40]))
    ta=lambda s,d:E("(function(){var v=__sp.LV.toAtomic(%r,%d);return v===null?null:v.toString()})()"%(s,d))
    ok('typed amounts become exact whole units: 1.5 SOL = 1500000000, 0.000001 USDC = 1, ".5" and "1." work, huge values stay exact',[ta('1.5',9),ta('0.000001',6),ta('.5',6),ta('1.',6),ta('0',6),ta('123456789012345678901234567890',6),ta('7',0)]==['1500000000','1','500000','1000000','0','123456789012345678901234567890000000','7'])
    ok('bad amounts are refused, not rounded: too many decimals, empty, ".", "1e5", "-1", "1,5", text, spaces inside',[ta(s,6) for s in ['0.0000001','','.','1e5','-1','1,5','abc','1 2']]==[None]*8 and ta('1.5',0)is None)
    fa=lambda v,d,m='undefined':E("__sp.LV.fromAtomic(%sn,%d,%s)"%(v,d,m))
    ok('amounts are shown correctly: 1.5, 0.000001, 0, 1,234,567.89, truncation to 2 places, negative',[fa(1500000000,9),fa(1,6),fa(0,9),fa(1234567890000,6),fa(123456789,6,2),fa(-5000000,6)]==['1.5','0.000001','0','1,234,567.89','123.45','-5'])
    P=lambda b:E("(function(){try{var t=__sp.LV.parseTx(__sp.LV.b64dec(%r));return {nSig:t.nSig,req:t.req,n:t.keys.length,payer:__sp.LV.b58enc(t.keys[0]),legacy:t.legacy}}catch(e){return 'ERR:'+e.message}})()"%base64.b64encode(b).decode())
    r=P(GOOD);ok('the transaction reader finds the signer count, the fee payer and the account list',r['nSig']==1 and r['req']==1 and r['n']==3 and r['payer']==ADDR and not r['legacy'],r)
    ok('it also reads legacy transactions, and refuses truncated or garbage ones (never crashes)',P(mk_tx(v0=False))['legacy']==True and all(str(P(b)).startswith('ERR') for b in [GOOD[:30],GOOD[:70],b'',b'\xff\xff\xff\xff\xff']))
    good={'inputMint':M['sol'],'outputMint':M['jup'],'inAmount':'500000000','outAmount':'250000000','otherAmountThreshold':'247500000','routePlan':[{'swapInfo':{'label':'Orca'}}],'priceImpactPct':'0.001'}
    def V(**o):
        q=dict(good);q.update(o);q={k:v for k,v in q.items() if v is not None}
        return E("(function(){try{var p={inT:{mint:%r},outT:{mint:%r}};__sp.LV.validate(%s,p,500000000n);return 'ok'}catch(e){return e.message}})()"%(M['sol'],M['jup'],json.dumps(q)))
    ok('a good quote passes',V()=='ok')
    ok('quotes that do not match the request are refused: wrong input token, wrong output token, wrong amount',all(V(**o)!='ok' for o in [{'inputMint':M['usdc']},{'outputMint':M['bonk']},{'inAmount':'500000001'}]))
    ok('quotes with no output, a non-numeric output, a minimum above the output, no route, or an error field are refused',all(V(**o)!='ok' for o in [{'outAmount':'0'},{'outAmount':'abc'},{'otherAmountThreshold':'999999999'},{'otherAmountThreshold':'x'},{'routePlan':[]},{'routePlan':None},{'error':'No routes found'}]))
    c.close()
    # ================= wallet connection
    c,pg,ST=page(wallet=False);E=pg.evaluate
    ok('no wallet in the window: a clear message and no connect button, no crash',E("document.querySelectorAll('[data-wallet]').length")==0 and 'No Solana wallet was found' in pg.inner_text('#lvBar'));c.close()
    c,pg,ST=page();E=pg.evaluate
    ok('a Wallet Standard wallet is discovered and offered by name',E("!!document.querySelector('[data-wallet=MockWallet]')") and 'Connect MockWallet' in pg.inner_text('#lvBar'))
    ok('the page never signs or connects by itself: nothing is called until you click',E("window.__wc.length")==0)
    connect(pg);ok('connecting works: address shown in the trade section and the header button, the wallet was asked only to connect',E("window.__wc")==['connect'] and ADDR[:4]+'..'+ADDR[-4:] in pg.inner_text('#lvBar') and pg.inner_text('#walletBtn')==ADDR[:4]+'..'+ADDR[-4:] and E("__sp.LV.S.addr")==ADDR)
    ok('balances come from the network: SOL 2.5, JUP 125.500001, BONK 9,876.54321, the Token-2022 token shown as unknown; zero balances hidden',all(s in pg.inner_text('#lvBal') for s in ['SOL','2.5','JUP','125.500001','BONK','9,876.54321','5']) and 'WIF' not in pg.inner_text('#lvBal') and '?' in pg.inner_text('#lvBal') and 'SOL 2.5' in pg.inner_text('#lvBar'),pg.inner_text('#lvBal')[:200])
    ok('both token programs were queried for balances',sorted({x[1][1]['programId'] for x in ST['rpc'] if x[0]=='getTokenAccountsByOwner'})==sorted([TOKENKEG,'TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb']))
    ST['sol']=1_000_000_000;pg.click('#lvRefresh');pg.wait_for_timeout(300);ok('Refresh balances re-reads the network',E("__sp.LV.S.bal['%s'].amount.toString()"%M['sol'])=='1000000000')
    ST['rpcfail']=True;pg.click('#lvRefresh');pg.wait_for_timeout(300);ok('when the RPC fails the page says so and keeps working','Could not load balances' in pg.inner_text('#lvBal') and 'answered 500' in pg.inner_text('#lvBal'));ST['rpcfail']=False;pg.click('#lvRefresh');pg.wait_for_timeout(300)
    E("window.__emit({accounts:[{address:'%s',publicKey:new Uint8Array(%s),chains:['solana:mainnet'],features:[]}]})"%(ADDR2,json.dumps(list(PK2))));pg.wait_for_timeout(300);ok('if the user switches account in the wallet, the page follows (new address, balances re-read)',E("__sp.LV.S.addr")==ADDR2 and ADDR2[:4]+'..'+ADDR2[-4:] in pg.inner_text('#lvBar'))
    E("window.__emit({accounts:[]})");pg.wait_for_timeout(200);ok('if the wallet disconnects itself, the page returns to the connect state',E("__sp.LV.S.addr")=='' and E("!!document.querySelector('[data-wallet]')"))
    c.close()
    c,pg,ST=page();E=pg.evaluate;E("window.__wo.noconnect=true");connect(pg);ok('a rejected connection is explained and nothing is connected','did not connect' in pg.inner_text('#lvMsg') and E("__sp.LV.S.addr")=='');c.close()
    c,pg,ST=page();E=pg.evaluate;connect(pg);pg.click('#lvDisc');pg.wait_for_timeout(200);ok('Disconnect clears the address, balances and history from the screen and tells the wallet',E("__sp.LV.S.addr")=='' and 'Connect a wallet to see your balances' in pg.inner_text('#lvBal') and 'disconnect' in E("window.__wc"));c.close()
    c,pg,ST=page(extra="window.addEventListener('wallet-standard:app-ready',function(e){e.detail.register({name:'NoSolana',chains:['ethereum:1'],accounts:[],features:{'standard:connect':{connect:async function(){}}}})});");E=pg.evaluate;ok('wallets that cannot sign Solana transactions are ignored',E("document.querySelectorAll('[data-wallet]').length")==1 and not E("!!document.querySelector('[data-wallet=NoSolana]')"));c.close()
    # ================= the ticket and quotes
    c,pg,ST=page();E=pg.evaluate;connect(pg)
    ok('the ticket starts on Buy JUP with SOL, slippage 1%, no quote and a disabled Review button',E("document.querySelector('[data-side=buy]').getAttribute('aria-pressed')")=='true' and E("document.getElementById('lvTok').value")=='jup' and E("document.getElementById('lvBase').value")=='sol' and E("document.querySelector('[data-slip=\"100\"]').getAttribute('aria-pressed')")=='true' and E("document.getElementById('lvGo').disabled") and 'Enter an amount' in pg.inner_text('#lvQuote'))
    n0=len(ST['quotes']);setamt(pg,'0.5');q=ST['quotes'][-1]
    ok('typing 0.5 asks Jupiter for exactly: SOL in, JUP out, 500000000 units, slippage 100 bps',len(ST['quotes'])==n0+1 and q['inputMint']==M['sol'] and q['outputMint']==M['jup'] and q['amount']=='500000000' and q['slippageBps']=='100',q)
    ok('the token details are checked on the network before quoting (JUP decimals asked for; SOL is not)',any(m=='getTokenSupply' and p[0]==M['jup'] for m,p in ST['rpc']) and not any(m=='getTokenSupply' and p[0]==M['sol'] for m,p in ST['rpc']))
    t=pg.inner_text('#lvQuote');ok('the quote shows what you pay, about what you get, the minimum, price impact, the route and the slippage',all(s in t for s in ['You pay      0.5 SOL','You receive  about 0.25 JUP','Minimum      0.2475 JUP','Price impact 0.120%','Route        Orca','Slippage     1%']),t)
    ok('Review is enabled once there is a valid quote',not E("document.getElementById('lvGo').disabled"))
    for v,exp in [('abc','Enter a number'),('0.0000000001','at most 9 decimals'),('-1','Enter a number'),('1e3','Enter a number'),('0','Enter an amount'),('','Enter an amount')]:
        n1=len(ST['quotes']);setamt(pg,v);ok('amount "%s" gets "%s" and no quote request'%(v,exp),exp in pg.inner_text('#lvQuote') and len(ST['quotes'])==n1 and E("document.getElementById('lvGo').disabled"),pg.inner_text('#lvQuote')[:60])
    setamt(pg,'0.5')
    for bps,sel in [(50,'[data-slip="50"]'),(300,'[data-slip="300"]')]:
        pg.click(sel);pg.wait_for_timeout(300);ok('the %s%% slippage chip sends slippageBps=%d'%(bps/100,bps),ST['quotes'][-1]['slippageBps']==str(bps))
    pg.fill('#lvSlip','2.5');pg.wait_for_timeout(300);ok('custom slippage 2.5% sends 250',ST['quotes'][-1]['slippageBps']=='250')
    n1=len(ST['quotes']);pg.fill('#lvSlip','7');pg.wait_for_timeout(300);ok('custom slippage above 5% is refused with a message and does not change the quote','at most 5%' in pg.inner_text('#lvMsg') and ST['quotes'][-1]['slippageBps']=='250')
    pg.fill('#lvSlip','0');pg.wait_for_timeout(200);ok('custom slippage of 0 is refused too','above 0' in pg.inner_text('#lvMsg'))
    pg.click('[data-slip="100"]');pg.wait_for_timeout(300)
    pg.select_option('#lvBase','usdc');pg.wait_for_timeout(200);ok('paying with USDC switches the quick amounts to 10 / 50 / 100 / 500',[b.inner_text() for b in pg.locator('#lvTicket [data-q]').all()]==['10','50','100','500'] and 'amount of USDC to spend' in pg.inner_text('#lvTicket'))
    pg.click('[data-q="50"]');pg.wait_for_timeout(300);q=ST['quotes'][-1];ok('50 USDC is sent as 50000000 (6 decimals)',q['inputMint']==M['usdc'] and q['amount']=='50000000')
    pg.select_option('#lvTok','bonk');pg.fill('#lvAmt','10');pg.wait_for_timeout(300);ok('BONK (5 decimals) shows correctly: 10 USDC at rate 0.5 gives 5 BONK','about 5 BONK' in pg.inner_text('#lvQuote'),pg.inner_text('#lvQuote'))
    pg.select_option('#lvTok','usdt');pg.select_option('#lvBase','usdt');pg.wait_for_timeout(200);ok('you cannot trade a token for itself: the token list moves off it',E("document.getElementById('lvTok').value")!='usdt' and not E("!!document.querySelector('#lvTok option[value=usdt]')"))
    pg.select_option('#lvBase','sol');pg.select_option('#lvTok','jup');pg.wait_for_timeout(200)
    # selling
    pg.click('[data-side=sell]');pg.wait_for_timeout(200);ok('Sell relabels the ticket and offers 25 / 50 / 75 / 100%','amount of JUP to sell' in pg.inner_text('#lvTicket') and 'receive' in pg.inner_text('#lvTicket') and E("document.querySelectorAll('#lvTicket [data-pct]').length")==4 and pg.inner_text('#lvGo')=='Review sell')
    pg.click('[data-pct="50"]');pg.wait_for_timeout(300);ok('50% of 125.500001 JUP is 62.75 (rounded down in whole units, never up) and the quote is for JUP in, SOL out',pg.input_value('#lvAmt')=='62.75' and ST['quotes'][-1]['inputMint']==M['jup'] and ST['quotes'][-1]['amount']=='62750000')
    pg.click('[data-pct="100"]');pg.wait_for_timeout(300);ok('100% is exactly the whole balance',pg.input_value('#lvAmt')=='125.500001' and ST['quotes'][-1]['amount']=='125500001')
    pg.select_option('#lvTok','sol') if False else None
    c.close()
    # ================= errors while quoting
    for name,cfg,exp in [('Jupiter 400',lambda S:S.update(quotefail=(400,{'error':'Could not find any route'})),'Could not find any route'),('Jupiter 500',lambda S:S.update(quotefail=(500,'<html>bad</html>')),'unreadable'),('network blocked',lambda S:S.update(jupabort=True),'could not reach Jupiter'),('a quote for the wrong token',lambda S:S.update(quotebad={'outputMint':M['bonk']}),'different pair'),('a quote for a different amount',lambda S:S.update(quotebad={'inAmount':'1'}),'different amount'),('a zero output',lambda S:S.update(quotebad={'outAmount':'0'}),'no output')]:
        c,pg,ST=page();E=pg.evaluate;cfg(ST);connect(pg);setamt(pg,'0.5');ok('quote problem "%s" is explained and the Review button stays disabled'%name,exp in pg.inner_text('#lvQuote') and E("document.getElementById('lvGo').disabled"),pg.inner_text('#lvQuote')[:90]);c.close()
    c,pg,ST=page();E=pg.evaluate;ST['decimals'][M['jup']]=9;connect(pg);setamt(pg,'0.5');ok('if the network says a listed token has different decimals than the page expects, trading it is blocked',"did not match" in pg.inner_text('#lvQuote') and E("document.getElementById('lvGo').disabled"));c.close()
    c,pg,ST=page();E=pg.evaluate;ST['rpcabort']=True;connect(pg);setamt(pg,'0.5');ok('with the RPC unreachable: balances and quote both explain it, nothing crashes','Could not load balances' in pg.inner_text('#lvBal') and 'could not verify' in pg.inner_text('#lvQuote'));c.close()
    # ================= review checks
    c,pg,ST=page();E=pg.evaluate;connect(pg);setamt(pg,'0.5');pg.click('#lvGo');pg.wait_for_timeout(300)
    s=pg.inner_text('#lvSummary');ok('Review shows the exact amounts, the wallet and BOTH full mint addresses, and says it is a real transaction',all(x in s for x in ['You pay      0.5 SOL','about 0.25 JUP','Minimum',ADDR,M['sol'],M['jup']]) and 'real transaction with real funds' in pg.inner_text('#mBody'))
    ok('nothing has been sent to the wallet yet (only connect)',E("window.__wc")==['connect'] and len(ST['swaps'])==0)
    pg.click('#lvCancel');ok('Cancel closes the review and still sends nothing',E("document.getElementById('modal').hidden") and E("window.__wc")==['connect'] and len(ST['swaps'])==0);c.close()
    c,pg,ST=page(wallet=True);E=pg.evaluate;setamt(pg,'0.5');pg.click('#lvGo');ok('trying to review without a connected wallet says to connect one','Connect a wallet to trade' in pg.inner_text('#lvMsg') and E("document.getElementById('modal').hidden"));c.close()
    c,pg,ST=page();E=pg.evaluate;connect(pg);setamt(pg,'3');pg.click('#lvGo');ok('spending more than you hold is refused with your actual balance','You only have 2.5 SOL' in pg.inner_text('#lvMsg') and E("document.getElementById('modal').hidden"))
    setamt(pg,'2.495');pg.click('#lvGo');ok('the 0.01 SOL fee reserve is enforced: 2.495 SOL is refused and the maximum (2.49) is shown','at least 0.01 SOL' in pg.inner_text('#lvMsg') and '2.49 SOL' in pg.inner_text('#lvMsg') and E("document.getElementById('modal').hidden"))
    setamt(pg,'2.49');pg.click('#lvGo');ok('exactly the maximum (2.49 SOL) is allowed, with a warning that it uses most of the balance','uses 99% of your SOL balance' in pg.inner_text('#mBody') and E("!!document.getElementById('lvAck')"));pg.click('#lvCancel');c.close()
    for imp,warn,block,label in [('0.0005',False,False,'0.05%'),('0.02',True,False,'2%'),('0.31',False,True,'31%')]:
        c,pg,ST=page();E=pg.evaluate;ST['impact']=imp;connect(pg);setamt(pg,'0.5');pg.click('#lvGo');pg.wait_for_timeout(200)
        if block:ok('a price impact of %s is blocked outright with an explanation'%label,E("document.getElementById('modal').hidden") and 'too high' in pg.inner_text('#lvMsg'))
        elif warn:ok('a price impact of %s shows a warning and Confirm stays disabled until you tick the box'%label,'noticeably worse price' in pg.inner_text('#mBody') and E("document.getElementById('lvConfirm').disabled") and (pg.check('#lvAck') or not E("document.getElementById('lvConfirm').disabled")))
        else:ok('a price impact of %s has no warning box and Confirm is enabled at once'%label,not E("!!document.getElementById('lvAck')") and not E("document.getElementById('lvConfirm').disabled"))
        c.close()
    c,pg,ST=page();E=pg.evaluate;connect(pg);setamt(pg,'0.5');pg.click('[data-slip="300"]');pg.wait_for_timeout(300);pg.click('#lvGo');ok('slippage of 3% or more adds a warning that needs a tick','Slippage is set to 3%' in pg.inner_text('#mBody') and E("!!document.getElementById('lvAck')"));pg.click('#lvCancel')
    E("__sp.LV.S.quote.at=Date.now()-31000");pg.click('#lvGo');ok('a quote older than 30 seconds cannot be used: it asks you to refresh',('more than 30 seconds' in pg.inner_text('#lvMsg')) and E("document.getElementById('modal').hidden"));c.close()
    # ================= executing a swap
    def go(ST=None,wopts=None,amt='0.5',pre=None):
        c,pg,ST=page(ST,wopts=wopts);connect(pg);
        if pre:pre(pg,ST)
        setamt(pg,amt);pg.click('#lvGo');pg.wait_for_timeout(200);return c,pg,ST
    c,pg,ST=go();E=pg.evaluate;qlast=ST['quotes'][-1];pg.click('#lvConfirm');pg.wait_for_timeout(900)
    SIG=b58e(bytes([7])*64)
    ok('Confirm builds the transaction from the SAME quote and your address (one request, wrapAndUnwrapSol on)',len(ST['swaps'])==1 and ST['swaps'][0]['userPublicKey']==ADDR and ST['swaps'][0]['quoteResponse']['inAmount']=='500000000' and ST['swaps'][0]['quoteResponse']['outputMint']==M['jup'] and ST['swaps'][0]['wrapAndUnwrapSol']==True)
    w=E("window.__sent");ok('the wallet receives exactly the bytes Jupiter built, for Solana mainnet and your account, once',E("window.__wc.filter(function(x){return x==='signAndSend'}).length")==1 and w['tx']==list(GOOD) and w['chain']=='solana:mainnet' and w['addr']==ADDR)
    ok('the signature from the wallet is shown in base58 and the status is tracked until confirmed','Confirmed on Solana' in pg.inner_text('#lvStatus') and SIG[:16] in pg.inner_text('#lvStatus') and 'swap confirmed' in pg.inner_text('#mTitle').lower())
    ok('the explorer link points at the signature and opens safely in a new tab',E("document.getElementById('lvLink').href")=='https://solscan.io/tx/'+SIG and E("document.getElementById('lvLink').target")=='_blank' and 'noopener' in E("document.getElementById('lvLink').rel"))
    ok('the swap is recorded (confirmed) with amounts, shown in your swaps list, the amount box is cleared and balances were re-read','done' in pg.inner_text('#lvHist') and '0.5 SOL to 0.25 JUP' in pg.inner_text('#lvHist') and pg.input_value('#lvAmt')=='' and sum(1 for m,_ in ST['rpc'] if m=='getBalance')>=2)
    ok('the confirm button is gone so it cannot be pressed twice',not E("document.getElementById('lvConfirm').offsetParent!==null"))
    pg.click('#mClose');pg.reload();pg.wait_for_timeout(1200);connect(pg);ok('after a reload and reconnect your swap history is still there (stored per address)','0.5 SOL to 0.25 JUP' in pg.inner_text('#lvHist'));c.close()
    c,pg,ST=go();E=pg.evaluate;ST['sigseq']=['failed'];pg.click('#lvConfirm');pg.wait_for_timeout(900);ok('a transaction that fails on-chain is reported as failed, with the explanation about the network fee, and recorded as failed','failed on-chain' in pg.inner_text('#lvStatus') and 'swap failed' in pg.inner_text('#mTitle').lower() and 'failed' in pg.inner_text('#lvHist'));c.close()
    c,pg,ST=go();E=pg.evaluate;ST['sigseq']=[None];pg.click('#lvConfirm');pg.wait_for_timeout(900);ok('a transaction that is not confirmed in time is reported as "sent, not confirmed" with the link, never as a success','Still not confirmed' in pg.inner_text('#lvStatus') and 'swap sent' in pg.inner_text('#mTitle').lower() and E("!!document.getElementById('lvLink')"));c.close()
    c,pg,ST=go();E=pg.evaluate;E("window.__wo.reject=true");pg.click('#lvConfirm');pg.wait_for_timeout(600);ok('declining in the wallet gives a calm message, records nothing and sends nothing','You declined the transaction' in pg.inner_text('#lvStatus') and 'None yet' in pg.inner_text('#lvHist') and len(ST['sent'])==0);c.close()
    for mode,exp in [('500','Jupiter could not build'),('error','Simulation failed'),('nofield','could not build'),('garbage','could not be read')]:
        st=mkstate();st['swapmode']=mode;c,pg,ST=go(st);E=pg.evaluate;pg.click('#lvConfirm');pg.wait_for_timeout(600);ok('swap build problem "%s" is explained and the wallet is never asked to sign'%mode,exp in pg.inner_text('#lvStatus') and 'signAndSend' not in E("window.__wc"));c.close()
    for name,tx,exp in [('a transaction paid for by a different account',mk_tx(payer=PK2),'different account'),('a transaction that does not use the Jupiter program',mk_tx(jup=False),'does not use the Jupiter program'),('a transaction needing two signatures',mk_tx(nsig=2,req=2),'more signatures'),('a truncated transaction',GOOD[:40],'could not be checked')]:
        st=mkstate();st['swaptx']=tx;c,pg,ST=go(st);E=pg.evaluate;pg.click('#lvConfirm');pg.wait_for_timeout(600);ok('SAFETY: %s is refused before it reaches the wallet'%name,exp in pg.inner_text('#lvStatus') and 'signAndSend' not in E("window.__wc") and 'signTransaction' not in E("window.__wc") and 'None yet' in pg.inner_text('#lvHist'),pg.inner_text('#lvStatus')[:120]);c.close()
    c,pg,ST=go(wopts={'send':False});E=pg.evaluate;pg.click('#lvConfirm');pg.wait_for_timeout(900);ok('a wallet that can only sign (not send) works: the page submits the signed transaction itself and tracks it',len(ST['sent'])==1 and base64.b64decode(ST['sent'][0])==GOOD and 'Confirmed on Solana' in pg.inner_text('#lvStatus'),len(ST['sent']));c.close()
    c,pg,ST=go();E=pg.evaluate;E("window.__wo.delay=400");pg.dblclick('#lvConfirm');pg.wait_for_timeout(1200);ok('double-clicking Confirm still builds and signs only ONE transaction',len(ST['swaps'])==1 and E("window.__wc.filter(function(x){return x==='signAndSend'}).length")==1);c.close()
    # ================= settings
    c,pg,ST=page();E=pg.evaluate;connect(pg);pg.click('#lvSet summary');pg.fill('#lvRpc','http://insecure.example/rpc');pg.click('#lvSetSave');ok('plain http:// addresses are refused','https://' in pg.inner_text('#lvMsg') and E("__sp.LV.LCFG.rpc")=='https://api.mainnet-beta.solana.com')
    pg.fill('#lvRpc','https://user:pass@rpc.example/x');pg.click('#lvSetSave');ok('addresses with a username or password in them are refused',E("__sp.LV.LCFG.rpc")=='https://api.mainnet-beta.solana.com')
    pg.fill('#lvRpc','not a url');pg.click('#lvSetSave');ok('text that is not an address is refused',E("__sp.LV.LCFG.rpc")=='https://api.mainnet-beta.solana.com')
    pg.fill('#lvRpc','https://rpc.example.org/');pg.fill('#lvJup','https://api.jup.ag/swap/v1');pg.click('#lvSetSave');ok('valid https addresses are saved (trailing slash removed) and shown in the note',E("__sp.LV.LCFG.rpc")=='https://rpc.example.org' and E("__sp.LV.LCFG.jup")=='https://api.jup.ag/swap/v1' and 'api.jup.ag' in pg.inner_text('#lvNote'))
    pg.reload();pg.wait_for_timeout(1200);ok('the settings persist across a reload',E("__sp.LV.LCFG.rpc")=='https://rpc.example.org' and pg.input_value('#lvJup')=='https://api.jup.ag/swap/v1')
    pg.click('#lvSet summary');pg.click('#lvSetReset');ok('Reset restores the defaults',E("__sp.LV.LCFG.jup")=='https://lite-api.jup.ag/swap/v1' and E("__sp.LV.LCFG.rpc")=='https://api.mainnet-beta.solana.com');c.close()
    # ================= custom tokens
    c,pg,ST=page();E=pg.evaluate;connect(pg);ST['decimals'][CUSTOM]=7
    pg.select_option('#lvTok','__custom');pg.wait_for_timeout(200);pg.fill('#lvMint','hello');pg.click('#lvMintGo');pg.wait_for_timeout(200);ok('the custom-token dialog refuses text that is not a mint address','not a valid Solana mint' in pg.inner_text('#lvMintInfo'))
    pg.fill('#lvMint',M['usdc']);pg.click('#lvMintGo');pg.wait_for_timeout(200);ok('a token that is already in the list is not added twice','already in the list' in pg.inner_text('#lvMintInfo'))
    pg.fill('#lvMint',ADDR);pg.click('#lvMintGo');pg.wait_for_timeout(300);ok('an address that is not a token mint is refused with the network\'s reason','Could not verify' in pg.inner_text('#lvMintInfo') and E("document.getElementById('lvMintUse').hidden"))
    pg.fill('#lvMint',CUSTOM);pg.click('#lvMintGo');pg.wait_for_timeout(300);ok('a real mint is looked up (7 decimals) and flagged as NOT verified, with the full address shown','7 decimals' in pg.inner_text('#lvMintInfo') and 'NOT on the verified list' in pg.inner_text('#lvMintInfo') and CUSTOM in pg.inner_text('#lvMintInfo'))
    pg.click('#lvMintUse');pg.wait_for_timeout(300);setamt(pg,'0.1');q=ST['quotes'][-1];ok('the custom token is then used with its own decimals and mint address in the quote request',q['outputMint']==CUSTOM and 'about 0.05' in pg.inner_text('#lvQuote'))
    pg.click('#lvGo');pg.wait_for_timeout(200);ok('reviewing a custom token shows a scam warning that must be ticked','not on the built-in list' in pg.inner_text('#mBody') and E("document.getElementById('lvConfirm').disabled") and CUSTOM in pg.inner_text('#lvSummary'));c.close()
    # ================= only the expected hosts are contacted and nothing else is loaded
    c,pg,ST=go();pg.click('#lvConfirm');pg.wait_for_timeout(700);E=pg.evaluate
    ok('the page only talks to the configured RPC and Jupiter hosts (plus the price service on the markets chart)',ST['hosts']<={'api.mainnet-beta.solana.com','lite-api.jup.ag'},ST['hosts'])
    ok('no scripts are loaded from outside the page',E("[].every.call(document.scripts,function(s){return !s.src})"));c.close()
    # ================= readability, accessibility, phone
    c,pg,ST=go();E=pg.evaluate;pg.click('#lvCancel')
    for th in ['green','amber','light']:
        E("__sp.setTheme('%s')"%th);pg.wait_for_timeout(900);a=E(AUDIT%"document.getElementById('trade')");ok('%s theme: all text in the trade section is readable with a wallet connected and a quote showing (%d blocks)'%(th,a['n']),not a['bad'],a['bad'][:3])
    E("__sp.setTheme('green')");pg.click('#lvGo');pg.wait_for_timeout(200);a=E(AUDIT%"document.querySelector('.mbox')");ok('the review dialog is readable',not a['bad'],a['bad'][:3]);pg.click('#lvCancel')
    ok('every control has an accessible name; the quote box is a live region; the balances table has a caption and headers',E("[].filter.call(document.querySelectorAll('#trade button,#trade input,#trade select'),function(e){var n=(e.getAttribute('aria-label')||e.textContent||'').trim();if(!n&&e.id){var l=document.querySelector('label[for=\"'+e.id+'\"]');n=l?l.textContent.trim():''}return !n}).length")==0 and E("document.getElementById('lvQuote').getAttribute('aria-live')")=='polite' and E("document.querySelector('#lvBal caption')!==null") and E("document.querySelectorAll('#lvBal th[scope=col]').length")==3);c.close()
    c,pg,ST=page(vp=(390,844),mobile=True);E=pg.evaluate;pg.tap('[data-wallet=MockWallet]');pg.wait_for_timeout(400);pg.tap('[data-q="0.5"]');pg.wait_for_timeout(300);pg.tap('#lvGo');pg.wait_for_timeout(300);pg.tap('#lvConfirm');pg.wait_for_timeout(1000)
    ok('phone: the whole flow works by tapping (connect, amount, review, confirm) and ends confirmed','Confirmed on Solana' in pg.inner_text('#lvStatus') and len(ST['swaps'])==1)
    pg.tap('#mClose');ok('phone: nothing scrolls sideways and every button is at least 36px tall',E("document.documentElement.scrollWidth")<=392 and not E("[].filter.call(document.querySelectorAll('#trade button'),function(b){return b.offsetParent!==null&&b.getBoundingClientRect().height<36}).length"),E("document.documentElement.scrollWidth"));c.close()
    ok('no page errors',not errs,errs[:3]);br.close()
print('\nSUMMARY: %d/%d passed'%(sum(1 for _,c in res if c),len(res)))
