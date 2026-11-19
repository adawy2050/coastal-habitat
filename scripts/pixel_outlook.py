"""Batched, training-only seasonal logistic models for individual SST cells.

All cells share climate predictors, but each has its own outcome history,
threshold, fitted coefficients and selected regularisation. Identical binary
training histories are solved once per origin/penalty for numerical efficiency.
"""
import numpy as np
from scipy.special import expit

ALPHAS=[.1,1.,10.,100.]


def design(years,x,test_year,test_x):
    bt=np.column_stack([np.ones(len(years)),years-years.mean()])
    be=np.array([[1.,test_year-years.mean()]])
    trend=np.linalg.lstsq(bt,x,rcond=None)[0]
    residual=x-bt@trend
    mean=residual.mean(axis=0);scale=np.maximum(residual.std(axis=0),1e-8)
    return np.column_stack([np.ones(len(years)),(residual-mean)/scale]),np.r_[1.,((np.array(test_x)[None,:]-be@trend-mean)/scale)[0]]


def solve_unique(d,labels,alpha):
    n,p=d.shape
    prevalence=(labels.sum(axis=1)+.5)/(n+1)
    beta=np.zeros((len(labels),p));beta[:,0]=np.log(prevalence/(1-prevalence))
    varying=(labels.sum(axis=1)>0)&(labels.sum(axis=1)<n)
    if not varying.any():return beta
    b=beta[varying].copy();y=labels[varying];penalty=np.array([1e-6]+[alpha]*(p-1))
    eye=np.diag(penalty)[None,:,:]
    for _ in range(35):
        probability=expit(b@d.T);w=np.maximum(probability*(1-probability),1e-8)
        gradient=(probability-y)@d+b*penalty
        hessian=(d.T[None,:,:]*w[:,None,:])@d[None,:,:]+eye
        step=np.linalg.solve(hessian,gradient[...,None])[...,0]
        b-=step/np.maximum(1.,np.max(np.abs(step),axis=1)/3.)[:,None]
        if np.max(np.abs(step))<1e-7:break
    beta[varying]=b
    return beta


def predict_all(years,x,outcomes,future_year,future_x,product):
    # outcomes: time x cells; group means may be appended as extra cells.
    n,c=outcomes.shape
    assert n>=12 and np.isfinite(outcomes).all()
    losses=np.full((4,n,c),np.nan,dtype=np.float64)
    probabilities=np.full((4,n,c),np.nan,dtype=np.float64)
    baseline=np.full((n,c),np.nan);truth=np.full((n,c),np.nan)
    current=np.empty((4,c));current_betas=np.empty((4,c,x.shape[1]+1))
    cutoffs=None
    for k in range(8,n+1):
        past=outcomes[:k].T
        cut=np.maximum(10.,np.quantile(past,.8,axis=1));labels=(past>cut[:,None]).astype(np.uint8)
        unique,inverse=np.unique(labels,axis=0,return_inverse=True)
        target_year=years[k] if k<n else future_year
        target_x=x[k] if k<n else future_x
        d,e=design(years[:k],x[:k],target_year,target_x)
        if k<n:
            baseline[k]=(labels.sum(axis=1)+.5)/(k+1)
            truth[k]=outcomes[k]>cut
        else:cutoffs=cut
        for j,alpha in enumerate(ALPHAS):
            beta=solve_unique(d,unique,alpha)
            p=expit(beta@e)[inverse]
            if k<n:
                probabilities[j,k]=p;losses[j,k]=(p-truth[k])**2
            else:
                current[j]=p;current_betas[j]=beta[inverse]
        if k%6==0 or k==n:print(product,'pixel origin',k,'unique label histories',len(unique),flush=True)
    selected=np.argmin(losses[:,max(8,n//2):n].mean(axis=1),axis=0)
    result={'probability':current[selected,np.arange(c)],'alpha':np.array(ALPHAS)[selected],
        'baseline':(np.sum(outcomes.T>cutoffs[:,None],axis=1)+.5)/(n+1),'threshold':cutoffs,
        'coefficients':current_betas[selected,np.arange(c)]}
    preds=[];observations=[];bases=[];test_years=[]
    for k in range(12,n):
        alpha=np.argmin(losses[:,max(8,k//2):k].mean(axis=1),axis=0)
        preds.append(probabilities[alpha,k,np.arange(c)])
        observations.append(truth[k]);bases.append(baseline[k]);test_years.append(years[k])
    pred=np.array(preds);observed=np.array(observations);base=np.array(bases);test_years=np.array(test_years)
    # Current target season determines issue month; evaluate baseline availability
    # using the canonical historical issue dates supplied by the caller below.
    result.update(predictions=pred,observations=observed,baselines=base,testYears=test_years,trainingYears=years)
    return result
