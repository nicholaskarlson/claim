# Base R working synthesis of college-level summaries.
d <- read.csv(commandArgs(trailingOnly=TRUE)[1], stringsAsFactors=FALSE)
k <- nrow(d)
n0 <- d$known_no
n1 <- d$known_offer
s0 <- d$sum_no
s1 <- d$sum_offer
delta <- (s1/n1-s0/n0)/100
v <- ((d$ss_no-s0^2/n0)/(n0-1)/n0+(d$ss_offer-s1^2/n1)/(n1-1)/n1)/10000
fit <- function(y,v) {
    w <- 1/v
    center <- weighted.mean(y,w)
    q <- sum((y-center)^2/v)
    c(fixed=center, q=q, tau2=max(0,(q-length(y)+1)/(sum(w)-sum(w^2)/sum(w))))
}
f <- fit(delta,v)
tau2 <- f[["tau2"]]
w <- 1/(v+tau2)
center <- weighted.mean(delta,w)
se <- sqrt(1/sum(w))
mean_half <- qt(.975,k-1)*se
pred_half <- qt(.975,k-2)*sqrt(se^2+tau2)
omitted <- vapply(seq_len(k), function(i) fit(delta[-i],v[-i])[["tau2"]], numeric(1))
counts <- c(n=sum(d$assigned_no+d$assigned_offer), known=sum(n0+n1))
vals <- c(colleges=k, roster=counts[["n"]], known=counts[["known"]],
          missing=counts[["n"]]-counts[["known"]], low=min(delta), high=max(delta),
          equal_mean=mean(delta), spread=sd(delta), common_ols=weighted.mean(delta,1/(1/n0+1/n1)),
          fixed_iv=f[["fixed"]], q=f[["q"]], tau=sqrt(tau2), pooled=center, mean_se=se,
          mean_lo=center-mean_half,mean_hi=center+mean_half,
          prediction_lo=center-pred_half, prediction_hi=center+pred_half,
          leaveout_lo=sqrt(min(omitted)),leaveout_hi=sqrt(max(omitted)),
          setNames(delta,paste0(d$college,"_contrast")), setNames(sqrt(v),paste0(d$college,"_se")))
options(digits=17)
write.table(data.frame(key=names(vals), value=unname(vals)), sep=",", row.names=FALSE,col.names=FALSE,quote=FALSE)
