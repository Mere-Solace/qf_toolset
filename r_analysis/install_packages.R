# Install required R packages for the analysis scripts
packages <- c(
  "readr", "dplyr", "tidyr", "lubridate", "zoo",
  "ggplot2", "broom", "car", "corrplot", "scales",
  "tidyverse", "reshape2", "stringr"
)

install_if_missing <- function(pkg) {
  if (!requireNamespace(pkg, quietly = TRUE)) {
    install.packages(pkg, repos = "https://cran.r-project.org")
  }
}

invisible(lapply(packages, install_if_missing))
cat("All packages installed.\n")
