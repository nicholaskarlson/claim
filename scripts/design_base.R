# Independent base R design calculations and exhaustive toy assignments.
args <- commandArgs(trailingOnly=TRUE)
a <- read.csv(args[2], colClasses="character", na.strings=NULL)
options(digits=17)
if (args[1] == "fixture") {
  college <- split(seq_len(nrow(a)), a$college_id)
  pairs <- lapply(college, function(ix) combn(ix, 2, simplify=FALSE))
  offers <- expand.grid(seq_along(pairs$A), seq_along(pairs$B))
  stats <- c("toy/schedules"=nrow(offers))
  for (v in 0:1) {
    y <- as.integer(ifelse(a$outcome=="", v, a$outcome))
    calc <- function(ix) mean(y[ix])-mean(y[-ix])
    exact <- mapply(function(i,j) calc(c(pairs$A[[i]], pairs$B[[j]])),
                    offers[[1]], offers[[2]])
    observed <- calc(which(a$offer=="1"))
    hits <- sum(abs(exact)>=abs(observed))
    values <- c(stat=observed, extremes=hits, p=hits/length(exact))
    stats <- c(stats, setNames(values, paste0("toy/if",v,"/",names(values))))
  }
  stats <- c(stats, "toy/max_p"=max(stats[c("toy/if0/p", "toy/if1/p")]))
} else {
  registry <- read.csv(args[3], colClasses="character", na.strings=NULL)
  a$y <- registry$withdrawal_label[match(a$student_id, registry$student_id)]
  bycollege <- split(a, a$college_id)
  stats <- c("design/n"=nrow(a), "design/colleges"=length(bycollege))
  lo <- hi <- var <- 0
  for (id in names(bycollege)) {
    d <- bycollege[[id]]
    y0 <- d$y[d$offer=="0"]
    y1 <- d$y[d$offer=="1"]
    counts <- c(n0=length(y0), n1=length(y1), y0=sum(y0=="1"), y1=sum(y1=="1"),
                m0=sum(y0==""), m1=sum(y1==""))
    stats <- c(stats, setNames(counts, paste("college",id,names(counts),sep="/")))
    nc <- nrow(d)
    w <- nc/nrow(a)
    lo <- lo + w*(mean(y1=="1")-mean(y0!="0"))
    hi <- hi + w*(mean(y1!="0")-mean(y0=="1"))
    var <- var + w^2*(nc/(nc-1))/4*(1/length(y0)+1/length(y1))
  }
  radius <- sqrt(var/.05)
  stats <- c(stats, "design/completion_lower"=lo, "design/completion_upper"=hi,
             "design/variance_bound"=var, "design/radius"=radius,
             "design/confidence_lower"=max(-1,lo-radius), "design/confidence_upper"=min(1,hi+radius))
}
write.table(data.frame(names(stats), stats), sep=",", quote=FALSE, row.names=FALSE, col.names=FALSE)
