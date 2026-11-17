# Base R rank and probability-loss calculations.
args <- commandArgs(trailingOnly=TRUE)
d <- read.csv(args[1], colClasses=c("character","integer","numeric","numeric"))
score <- function(rows) {
  y <- rows$outcome
  n <- length(y)
  e <- sum(y)
  v <- c(n=n,events=e)
  for (method in c("forecast","baseline")) {
    p <- rows[[method]]
    # The rank sum subtracts the within-event pairs.
    pairs2 <- 2*sum(rank(p,ties.method="average")[y==1])-e*(e+1)
    clip <- pmin(1-1e-12,pmax(1e-12,p))
    stats <- c(mean=mean(p),brier=mean((p-y)^2),auc_pairs2=pairs2,auc=pairs2/(2*e*(n-e)),
               log_loss=-mean(ifelse(y==1,log(clip),log1p(-clip))))
    v <- c(v,setNames(stats,paste(method,names(stats),sep="/")))
  }
  binned <- cut(rows$forecast,breaks=(0:5)/5,right=FALSE,include.lowest=TRUE,labels=FALSE)
  for (i in 1:5) {
    key <- paste0("bin/",i,"/")
    use <- binned==i
    stats <- c(n=sum(use),events=sum(y[use]))
    if (any(use)) stats <- c(stats,mean=mean(rows$forecast[use]))
    v <- c(v,setNames(stats,paste0(key,names(stats))))
  }
  v
}
options(digits=17)
for (g in c("all",sort(unique(d$group)))) {
  vals <- score(if (g=="all") d else d[d$group==g,])
  write.table(data.frame(paste(g,names(vals),sep="/"),vals),sep=",",row.names=FALSE,col.names=FALSE,quote=FALSE)
}
