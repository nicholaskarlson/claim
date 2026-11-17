# Base R route. Each join and calculation is independent of the Python routes.
args <- commandArgs(trailingOnly = TRUE)
mode <- args[[1]]
input <- args[[2]]
out <- args[[3]]
values <- c()
joined <- data.frame(student_id=character(),college_id=character(),offer=character(),
                     outcome_known=character(),withdrawal_label=character(),exit_type=character())
read <- function(path) read.csv(path, colClasses="character", na.strings=NULL, check.names=FALSE)
if (mode == "withdrawal") {
    assigned <- read(input)
    registry <- read(args[[4]])
    assigned <- assigned[order(assigned$student_id), ]
    index <- match(assigned$student_id,registry$student_id)
    if (anyNA(index)) stop("Missing registry identity")
    observed <- registry[index, ]
    if (any(assigned$offer != observed$offer)) stop("Offer disagrees across files")
    joined <- cbind(assigned,observed[c("outcome_known","withdrawal_label","exit_type")])
    values <- c(baseline_n=nrow(assigned),registry_n=nrow(registry),colleges_n=length(unique(assigned$college_id)))
    for (arm in c("0","1")) {
        rows <- joined[joined$offer == arm, ]
        n <- nrow(rows)
        known <- sum(rows$outcome_known == "1")
        events <- sum(rows$withdrawal_label == "1")
        unknown <- n-known
        result <- c(assigned=n,known=known,unknown=unknown,events=events,recorded_rate=events/n,
                    known_rate=if (known > 0) events/known else NA_real_,lower=events/n,upper=(events+unknown)/n)
        names(result) <- paste0("arm/",arm,"/",names(result))
        values <- c(values,result)
    }
    values[["known_difference"]] <- values[["arm/1/known_rate"]]-values[["arm/0/known_rate"]]
    values[["realized_difference_lower"]] <- values[["arm/1/lower"]]-values[["arm/0/upper"]]
    values[["realized_difference_upper"]] <- values[["arm/1/upper"]]-values[["arm/0/lower"]]
} else {
    sampling <- read(file.path(input,"sampling.csv"))
    selections <- combn(seq_len(nrow(sampling)),as.integer(sampling$sample_colleges[[1]]))
    estimates <- apply(selections,2,function(i) sum(as.integer(sampling$withdrawals[i]))/sum(as.integer(sampling$size[i])))
    values <- c("sampling/schedules"=ncol(selections),"sampling/population_rate"=
                sum(as.integer(sampling$withdrawals))/sum(as.integer(sampling$size)),
                "sampling/mean"=mean(estimates),"sampling/min"=min(estimates),"sampling/max"=max(estimates))
    assigned <- read(file.path(input,"assignment.csv"))
    y <- as.integer(assigned$outcome)
    observed <- which(assigned$offer == "1")
    contrast <- function(i) mean(y[i])-mean(y[-i])
    choices <- lapply(split(seq_along(y),assigned$college_id),function(i) combn(i,as.integer(assigned$offers_per_college[[1]])))
    schedules <- expand.grid(lapply(choices,function(x) seq_len(ncol(x))))
    blocked <- lapply(seq_len(nrow(schedules)),function(i) unlist(lapply(seq_along(choices),function(j) choices[[j]][,schedules[i,j]])))
    pooled <- as.list(as.data.frame(combn(seq_along(y),length(observed))))
    observed_difference <- contrast(observed)
    values[["assignment/observed_difference"]] <- observed_difference
    for (name in c("blocked","pooled")) {
        selected <- if (name == "blocked") blocked else pooled
        extremes <- sum(vapply(selected,function(i) abs(contrast(i)) >= abs(observed_difference)-1e-14,logical(1)))
        result <- c(length(selected),extremes,extremes/length(selected))
        names(result) <- paste0("assignment/",name,c("_schedules","_extremes","_p"))
        values <- c(values,result)
    }
    model <- read(file.path(input,"model.csv"))
    likelihoods <- dbinom(as.integer(model$events),as.integer(model$trials),as.numeric(model$probability))
    names(likelihoods) <- paste0("model/likelihood_",seq_along(likelihoods)-1)
    values <- c(values,likelihoods,"model/likelihood_ratio"=unname(likelihoods[[1]]/likelihoods[[2]]))
}
dir.create(out,recursive=TRUE)
write.table(data.frame(key=names(values),value=ifelse(is.na(values),"",sprintf("%.17g",values))),
            file.path(out,"values.csv"),sep=",",row.names=FALSE,quote=FALSE)
write.table(joined,file.path(out,"joined.csv"),sep=",",row.names=FALSE,quote=FALSE)
