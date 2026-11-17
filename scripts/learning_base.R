# Independent base R table, qnorm/pnorm and normal predictive densities.
a <- commandArgs(trailingOnly=TRUE)
d <- read.csv(a[2],colClasses='character',na.strings=NULL,check.names=FALSE)
out <- c()
if(a[1]=='screen') {
 stopifnot(identical(names(d),c('student_id','college_id','intention','exit_month','label')),nrow(d)>0,!anyDuplicated(d$student_id),all(nzchar(d$student_id)),all(nzchar(d$college_id)),all(d$intention %in% c('','0','1')),all(d$label %in% c('','0','1')))
 time <- as.numeric(d$exit_month); stopifnot(all(is.finite(time)),all(time>=0 & time<=12))
 e <- d[time>3,];s <- e[e$intention!='',];k <- s[s$label!='',]
 cell <- function(x,y) sum(k$intention==x & k$label==y)
 tp<-cell('1','1');fp<-cell('1','0');fn<-cell('0','1');tn<-cell('0','0')
 up<-sum(s$intention=='1' & s$label=='');un<-sum(s$intention=='0' & s$label=='')
 stopifnot(min(tp+fn,fp+tn,tp+fp)>0)
 h<-tp/(tp+fn);f<-fp/(fp+tn);valid<-h>0 & h<1 & f>0 & f<1
 out<-c(total=nrow(d),eligible=nrow(e),scorable=nrow(s),known=nrow(k),unknown=up+un,positive_unknown=up,negative_unknown=un,tp=tp,fp=fp,fn=fn,tn=tn,hit=h,false_alarm=f,ppv=tp/(tp+fp),coverage=nrow(s)/nrow(e),hit_low=tp/(tp+fn+un),hit_high=(tp+up)/(tp+fn+up),ppv_low=tp/(tp+fp+up),ppv_high=(tp+up)/(tp+fp+up),raw_probit_defined=as.numeric(valid))
 if(valid) out<-c(out,d_prime=qnorm(h)-qnorm(f),criterion=-(qnorm(h)+qnorm(f))/2)
} else {
 stopifnot(nrow(d)>0,!anyDuplicated(d$case))
 for(i in seq_len(nrow(d))) {
  y<-as.numeric(d$estimate_pp[i]);s<-as.numeric(d$se_pp[i]);t<-as.numeric(d$prior_sd_pp[i]);margin<-as.numeric(d$margin_pp[i])
  stopifnot(all(is.finite(c(y,s,t,margin))),s>0,t>0,margin>=0)
  shrink<-t^2/(t^2+s^2);m<-shrink*y;sd<-sqrt(shrink)*s
  v<-c(mean=m,sd=sd,lo95=qnorm(.025,m,sd),hi95=qnorm(.975,m,sd),p_negative=pnorm(0,m,sd),p_benefit=pnorm(-margin,m,sd),bf01=dnorm(y,0,s)/dnorm(y,0,sqrt(t^2+s^2)))
  names(v)<-paste(d$case[i],names(v),sep='/');out<-c(out,v)
 }
}
for(k in names(out)) cat(k,format(out[[k]],digits=17,scientific=TRUE),sep=',',fill=TRUE)
