# Base R computation for Chapter 4.
args <- commandArgs(trailingOnly=TRUE)
options(digits=17)
b <- read.csv(args[1], na.strings="", colClasses="character")
a <- read.csv(args[2], colClasses="character")
f <- read.csv(args[3], na.strings="", colClasses="character")
score <- function(d) {
  z <- sapply(d[paste0("st", 1:5)], as.integer)
  z[,4] <- 6L - z[,4]
  n <- rowSums(!is.na(z))
  ifelse(n >= 4, rowSums(z, na.rm=TRUE) * (20 / n), NA)
}
id <- b$student_id
stopifnot(setequal(id, a$student_id), setequal(id, f$student_id))
f <- f[match(id, f$student_id),]
eligible <- data.frame(id=id, x=score(b), y=ifelse(f$responded == "1", score(f), NA))
eligible <- eligible[a$offer[match(id, a$student_id)] == "0" & !is.na(eligible$x),]
eligible <- eligible[order(eligible$x, eligible$id, method="radix"),]
pair <- eligible[!is.na(eligible$y),]
m <- nrow(pair) %/% 4
low <- head(pair, m)
high <- tail(pair, m)
high_all <- pair[pair$x >= high$x[1],]
selected <- tail(eligible, nrow(eligible) %/% 4)
threshold <- pair$y[pair$x >= 80]
fit <- lm(I(y / 20) ~ I(x / 20), data=pair)
values <- c(
  "arm0/n"=nrow(pair), "arm0/baseline_mean"=mean(pair$x)/20, "arm0/month3_mean"=mean(pair$y)/20,
  "arm0/change"=mean(pair$y-pair$x)/20, "arm0/correlation"=cor(pair$x,pair$y),
  "arm0/slope"=unname(coef(fit)[2]), "threshold/n"=length(threshold),
  "threshold/remain"=sum(threshold >= 80), "baseline_selected/eligible"=nrow(eligible),
  "baseline_selected/top/n"=nrow(selected), "baseline_selected/top/paired"=sum(!is.na(selected$y)),
  "top/ties"=sum(pair$x == high$x[1]), "top/prediction"=unname(predict(fit, data.frame(x=mean(high$x))))
)
for (name in c("bottom", "top", "top_inclusive")) {
  group <- switch(name, bottom=low, top=high, top_inclusive=high_all)
  measures <- c(n=nrow(group), baseline=mean(group$x)/20, month3=mean(group$y)/20, change=mean(group$y-group$x)/20)
  names(measures) <- paste(name, names(measures), sep="/")
  values <- c(values, measures)
}
rx <- c(.70,.70,.70,.10)
ry <- c(.85,.85,.85,.10)
error_r <- c(-.25,0,.25,0)
residual_cov <- as.numeric(args[4]) - error_r * sqrt((1-rx)*(1-ry))
implied <- residual_cov / (sqrt(rx)*sqrt(ry))
scenarios <- c("negative","zero","positive","impossible")
values <- c(values, setNames(implied, paste0("error/",scenarios,"/rho")),
            setNames(as.integer(abs(implied) <= 1), paste0("error/",scenarios,"/feasible")))
write.table(data.frame(key=names(values),value=values), sep=",", quote=FALSE, row.names=FALSE, col.names=FALSE)
write.table(eligible, sep=",", quote=FALSE, row.names=FALSE, col.names=FALSE, na="")
