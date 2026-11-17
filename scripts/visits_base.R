# Base R visit/exposure summaries and working college covariance.
args <- commandArgs(trailingOnly=TRUE)
d <- read.csv(args[2], colClasses="character")
if (args[1]=="ordinary") {
  a <- read.csv(args[3], colClasses="character")
  d <- cbind(a, d[match(a$student_id,d$student_id), setdiff(names(d),"student_id")])
}
y <- as.integer(d$visits)
t <- as.numeric(d$months)
z <- as.integer(d$offer)
if (any(t <= 0)) stop("Exposure must be positive")
stats <- c("raw/zeros"=sum(y==0))
for (arm in 0:1) {
  i <- z==arm
  s <- c(n=sum(i),visits=sum(y[i]),months=sum(t[i]),mean_count=mean(y[i]),
         aggregate_rate=sum(y[i])/sum(t[i]),mean_individual_rate=mean(y[i]/t[i]))
  stats <- c(stats,setNames(s,paste0("arm",arm,"/",names(s))))
}
stats <- c(stats,
  "raw/count_difference"=unname(stats["arm1/mean_count"]-stats["arm0/mean_count"]),
  "raw/rate_ratio"=unname(stats["arm1/aggregate_rate"]/stats["arm0/aggregate_rate"]))
if (args[1]=="ordinary") {
  beta <- as.numeric(args[4:8])
  x <- cbind(1,z,as.numeric(d$prior_grade)-3,as.integer(d$part_time),as.integer(d$first_gen))
  n <- nrow(x)
  k <- ncol(x)
  mu <- as.vector(t*exp(x %*% beta))
  s <- (y-mu)*x
  info <- crossprod(x,x*mu)
  v <- as.vector(s %*% chol2inv(chol(info))[,2])
  grouped <- as.vector(rowsum(v,d$college_id))
  g <- length(grouped)
  row_se <- sqrt(sum(v^2)*n/(n-k))
  college_se <- sqrt(sum(grouped^2)*(g/(g-1))*((n-1)/(n-k)))
  difference <- vapply(split(seq_len(n),d$college_id), function(i) {
    (length(i)/n)*(mean(y[i][z[i]==1])-mean(y[i][z[i]==0]))
  }, numeric(1))
  radius <- qt(.975,g-1)*college_se
  stats <- c(stats,"design/colleges"=g,"design/difference"=sum(difference),
             "model/row_se"=row_se,"model/college_se"=college_se,
             "model/score_max_per_row"=max(abs(colSums(s)))/n,
             "model/college_lower"=exp(beta[2]-radius),"model/college_upper"=exp(beta[2]+radius))
}
options(digits=17)
write.table(data.frame(names(stats),stats),sep=",",row.names=FALSE,col.names=FALSE,quote=FALSE)
