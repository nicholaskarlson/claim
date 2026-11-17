# Independent base R counts and poststratification.
args <- commandArgs(trailingOnly=TRUE)
d <- read.csv(args[2], colClasses="character", na.strings=NULL)
options(digits=17)
rates <- function(n, k, y) {
  c(eligible=n, known=k, withdrawals=y, unknown=n-k, known_rate=y/k, lower=y/n, upper=(y+n-k)/n)
}
if (args[1] == "fixture") {
  n <- as.integer(d$eligible)
  k <- as.integer(d$known)
  y <- as.integer(d$withdrawals)
  if (any(k == 0)) stop("A target stratum has no known outcomes")
  w <- n / k
  v <- c(rates(sum(n), sum(k), sum(y)), weighted=weighted.mean(y/k, n),
         weight_sum=sum(w*k), setNames(w, paste0("weight_", d$stratum)))
  names(v) <- paste0("fixture/", names(v))
} else {
  groups <- list(all=d, respondents=subset(d, responded_baseline=="1"),
                 nonrespondents=subset(d, responded_baseline=="0"))
  v <- numeric()
  for (name in names(groups)) {
    g <- groups[[name]]
    ans <- c(rates(nrow(g), sum(g$outcome_known=="1"), sum(g$withdrawal_label=="1")),
             transfers=sum(g$exit_type=="transfer"))
    v <- c(v, setNames(ans, paste(name, names(ans), sep="/")))
  }
  ctrl <- subset(groups$respondents, offer=="0" & outcome_known=="1")
  blend <- weighted.mean(c(mean(ctrl$withdrawal_label=="1"), v["nonrespondents/known_rate"]),
                         c(nrow(groups$respondents), nrow(groups$nonrespondents)))
  v <- c(v, "audit/old_response_blend"=blend)
}
write.table(data.frame(names(v), v), sep=",", quote=FALSE, row.names=FALSE, col.names=FALSE)
