from pathlib import Path
import json
o=Path(__file__).resolve().parent
def calculate(growth,cap,rate,loss):
    price=24259.1; area=14600000*.93; debt=price*.4
    annual_noi=3492*4/10; rent0=area*98*12/1e7; netcost=rent0-annual_noi
    pay=debt*rate/(1-(1+rate)**-20)
    balance=debt; uc=[-price*1.02]; ec=[-price*1.02+debt-debt*.01]; dscr=[]
    for y in range(1,12):
        rent=area*12/1e7*(98*1.03**(y-1) if y<=5 else 105*(1+growth)**(y-1)*(.7+.3*.5 if y==6 else 1))
        noi=rent*(1-loss)-netcost*1.03**(y-1)
        reserve=area*30*1.03**(y-1)/1e7
        ti=area*.3*(500+105*12*(1+growth)**(y-1)*.1)/1e7 if y==6 else 0
        if y==11:
            sale=noi/cap*.98;uc[-1]+=sale;ec[-1]+=sale-balance;break
        balance-=pay-balance*rate
        dscr.append(noi/pay);uc.append(noi-reserve-ti);ec.append(noi-reserve-ti-pay)
    def irr(cf):
        lo=-.9;hi=1
        for _ in range(150):
            mid=(lo+hi)/2;npv=sum(x/(1+mid)**t for t,x in enumerate(cf))
            if npv>0:lo=mid
            else:hi=mid
        return (lo+hi)/2
    return [irr(ec),irr(uc),sum(max(x,0) for x in ec)/sum(-min(x,0) for x in ec),min(dscr),ec[1]/-ec[0],sum(x/1.1**t for t,x in enumerate(uc))]
v=json.loads((o/'Embassy_Model_Validation.json').read_text())
comparison={}
for key,args in [('base',(.03,.065,.08,0)),('upside',(.05,.06,.075,0)),('downside',(.01,.075,.095,.02))]:
    independent=calculate(*args);cached=[x[0] for x in v[key]][:6]
    errors=[abs(a-b) for a,b in zip(independent,cached)]
    assert max(errors)<1e-5,(key,errors)
    comparison[key]={'independent':independent,'max_absolute_difference':max(errors)}
(o/'Independent_Model_Check.json').write_text(json.dumps(comparison,indent=2))

print("All three scenarios match the workbook calculation evidence.")
