# Base R normal-reference intervals, tests and power.
rows <- read.csv(commandArgs(trailingOnly=TRUE)[1])
d <- rows$estimate_pp
se <- rows$se_pp
m <- rows$margin_pp
lo95 <- d - qnorm(.975)*se
hi95 <- d + qnorm(.975)*se
lo90 <- d - qnorm(.95)*se
hi90 <- d + qnorm(.95)*se
p_lower <- pnorm(-m,d,se)
p_upper <- pnorm(m,d,se,lower.tail=FALSE)
p_equiv <- pmax(p_lower,p_upper)
p_diff <- 2*pnorm(-abs(d),0,se)
cdf_edge <- pnorm(m-qnorm(.95)*se,0,se)
values <- data.frame(estimate=d, se=se, margin=m, lo95=lo95, hi95=hi95, lo90=lo90, hi90=hi90,
                     p_difference=p_diff, p_lower=p_lower, p_upper=p_upper, p_equivalence=p_equiv,
                     different=as.integer(p_diff<.05), equivalent=as.integer(lo90 > -m & hi90 < m),
                     benefit_beyond_margin=as.integer(pnorm(-m,d,se,lower.tail=FALSE)<.05),
                     power_zero=pmax(0,2*cdf_edge-1))
options(digits=17)
for (i in seq_len(nrow(rows))) {
    output <- data.frame(key=paste(rows$case[i],names(values),sep="/"), value=unlist(values[i,]))
    write.table(output,sep=",",row.names=FALSE,col.names=FALSE,quote=FALSE)
}
