# Base R route for the scoped observed-score check.
path <- commandArgs(trailingOnly = TRUE)[[1]]
data <- read.csv(path, na.strings = "", stringsAsFactors = FALSE)
stress <- paste0("st", 1:5)
wellbeing <- paste0("wb", 1:5)
keep <- complete.cases(data[c(stress, wellbeing)])
complete <- data[keep, ]
complete$st4 <- 6L - complete$st4
complete$wb4 <- 6L - complete$wb4
x <- rowSums(complete[stress])
y <- rowSums(complete[wellbeing])
cat(sprintf("%d,%d,%d,%.17g\n", nrow(data), length(unique(data$college_id)),
            nrow(complete), cor(x / 5, y / 5, method = "pearson")))
for (i in seq_along(x)) cat(sprintf("%s,%d,%d\n", complete$student_id[i], x[i], y[i]))
