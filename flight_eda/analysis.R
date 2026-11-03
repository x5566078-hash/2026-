# 題目 E：缺失值的處理方式會不會改變 PCA 看到的結構？
# 執行：Rscript analysis.R
# 只使用 R 內建函式；從 data/raw 讀資料，成果寫入 output/r，不覆蓋 Python 報告。
# 本程式處理報告的第 2–4 部分。第 1 部分 AI 初版與第 5 部分個人反思見既有報告。

args <- commandArgs(trailingOnly = FALSE)
file_arg <- grep("^--file=", args, value = TRUE)
if (length(file_arg) != 1L) stop("請用 Rscript analysis.R 執行")
root <- normalizePath(dirname(sub("^--file=", "", file_arg)))
out <- file.path(root, "output", "r")
dir.create(out, recursive = TRUE, showWarnings = FALSE)

flight_vars <- c("dep_delay", "arr_delay", "air_time", "distance")
weather_vars <- c("temp", "dewp", "humid", "wind_speed", "precip", "visib", "pressure")
vars <- c(flight_vars, weather_vars)
write_table <- function(x, name) {
  write.csv(x, file.path(out, paste0(name, ".csv")), row.names = FALSE, na = "")
}
key <- function(x) paste(x$origin, x$time_hour, sep = "|")
cat("讀取原始資料...\n")
flights <- read.csv(file.path(root, "data/raw/flights.csv"), stringsAsFactors = FALSE)
weather <- read.csv(file.path(root, "data/raw/weather.csv"), stringsAsFactors = FALSE)
stopifnot(nrow(flights) == 336776L, nrow(weather) == 26115L)
stopifnot(!anyDuplicated(key(weather)), !anyDuplicated(flights$rownames))

# ── 第 2 部分：缺失值診斷 ─────────────────────────────────────────────
# 左連接的主表是航班。用 origin + UTC time_hour 找逐時天氣，保留未配對航班。
flight_key <- key(flights)
weather_key <- key(weather)
hour_keys <- unique(rbind(weather[c("origin", "time_hour")],
                          flights[c("origin", "time_hour")]))
hour_index <- match(key(hour_keys), weather_key)
hourly <- hour_keys
for (v in weather_vars) hourly[[v]] <- weather[[v]][hour_index]
hourly$unmatched <- is.na(hour_index)

# 可疑的 1,048 mph 風速只在分析副本改成 NA，原始 CSV 維持原狀。
hourly$wind_qc <- !is.na(hourly$wind_speed) & hourly$wind_speed > 100
hourly$wind_speed[hourly$wind_qc] <- NA_real_
flight_hour_index <- match(flight_key, key(hourly))
stopifnot(!anyNA(flight_hour_index))
d <- cbind(flights, hourly[flight_hour_index,
                           c(weather_vars, "unmatched", "wind_qc"), drop = FALSE])
rownames(d) <- NULL

# 航班結果不適用與天氣缺失分開處理：沒有出發紀錄時，不創造延誤真值。
d$eligible <- complete.cases(d[flight_vars])
d$status <- ifelse(is.na(d$dep_time), "no_departure",
                   ifelse(d$eligible, "eligible", "other_incomplete"))
d$weather_missing <- !complete.cases(d[weather_vars])
stopifnot(nrow(d) == nrow(flights), sum(d$eligible) == 327346L,
          sum(d$unmatched) == 1556L)
write_table(as.data.frame(table(d$status)), "flight_status")

# 原始欄位缺失以各來源表為母體；合併後缺失以航班為母體，兩者不可混算。
provenance <- do.call(rbind, lapply(vars, function(v) {
  source <- if (v %in% flight_vars) flights else weather
  data.frame(variable = v,
             source_unit = if (v %in% flight_vars) "flight" else "station_hour",
             source_n = nrow(source), source_missing_n = sum(is.na(source[[v]])),
             joined_missing_n = sum(is.na(d[[v]])),
             unmatched_contribution_n = if (v %in% flight_vars) 0L else sum(d$unmatched),
             qc_added_missing_n = if (v == "wind_speed") sum(d$wind_qc) else 0L,
             joined_missing_pct = 100 * mean(is.na(d[[v]])))
}))
write_table(provenance, "missing_provenance")

# 共同缺失矩陣：元素 (i,j) 是兩欄同時缺失的航班數。
missing <- is.na(d[vars]) * 1L
co_missing <- crossprod(as.matrix(missing))
write.csv(co_missing, file.path(out, "co_missing_counts.csv"))
phi <- suppressWarnings(cor(missing))
write.csv(phi, file.path(out, "co_missing_phi.csv"))

# 氣壓在原始逐時天氣表的有／無缺失比較，用於評估簡單 MCAR 假設。
pressure_group <- do.call(rbind, lapply(c(FALSE, TRUE), function(flag) {
  x <- weather[is.na(weather$pressure) == flag, ]
  data.frame(pressure_missing = flag, station_hours = nrow(x),
             rain_pct = 100 * mean(x$precip > 0),
             humid_mean = mean(x$humid, na.rm = TRUE),
             visib_mean = mean(x$visib, na.rm = TRUE))
}))
write_table(pressure_group, "pressure_groups")

# 只在抵達延誤可觀測的適用母體比較，避免把取消代理航班當成零延誤。
eligible <- d[d$eligible, ]
missing_group <- do.call(rbind, lapply(c(FALSE, TRUE), function(flag) {
  x <- eligible[is.na(eligible$pressure) == flag, ]
  data.frame(pressure_missing = flag, flights = nrow(x),
             arr_delay_mean = mean(x$arr_delay),
             distance_mean = mean(x$distance))
}))
write_table(missing_group, "missing_vs_observed")

# 缺失矩陣只抽樣作圖，以上表格和後續 PCA 都使用全資料。
png(file.path(out, "missingness.png"), width = 1500, height = 650, res = 140)
par(mfrow = c(1, 2), mar = c(9, 5, 3, 2))
set.seed(20261026)
sample_id <- sort(sample.int(nrow(d), 2000))
image(t(as.matrix(missing[sample_id, ])), col = c("#e4eeee", "#cc674c"),
      axes = FALSE, main = "Missingness matrix (red = missing)",
      xlab = "2,000 sampled flights")
axis(2, at = seq(0, 1, length.out = length(vars)), labels = vars, las = 2, cex.axis = .65)
image(seq_along(vars), seq_along(vars), phi, zlim = c(-1, 1),
      col = colorRampPalette(c("#2166ac", "white", "#b2182b"))(100),
      axes = FALSE, main = "Co-missingness (phi)", xlab = "", ylab = "")
axis(1, at = seq_along(vars), labels = vars, las = 2, cex.axis = .55)
axis(2, at = seq_along(vars), labels = vars, las = 2, cex.axis = .55)
dev.off()

# ── 第 3 部分：三種缺失處理策略 ────────────────────────────────────────
# CCA：只保留 11 個連續變數完整的適用航班。
x_raw <- as.matrix(eligible[vars])
storage.mode(x_raw) <- "double"
cc <- complete.cases(x_raw)
stopifnot(sum(cc) == 291140L)
x_cca <- x_raw[cc, , drop = FALSE]
eligible_hour_index <- flight_hour_index[d$eligible]

# MEAN：在逐時天氣表層級填各欄均值，同一時點的多班航班共用一個值。
hour_x <- as.matrix(hourly[weather_vars])
storage.mode(hour_x) <- "double"
hour_mean <- colMeans(hour_x, na.rm = TRUE)
mean_hour_x <- hour_x
for (j in seq_along(weather_vars)) {
  miss <- is.na(mean_hour_x[, j])
  mean_hour_x[miss, j] <- hour_mean[j]
}
x_mean <- x_raw
x_mean[, weather_vars] <- mean_hour_x[eligible_hour_index, , drop = FALSE]

# HOTDECK：同機場、同「紐約當地月份」找 5 個完整天氣供體。
# 距離使用可觀測天氣、月內日期與循環小時；整筆未配對時只能靠時間。
utc_time <- as.POSIXct(hourly$time_hour, format = "%Y-%m-%dT%H:%M:%SZ", tz = "UTC")
stopifnot(!anyNA(utc_time))
local_month <- as.integer(format(utc_time, "%m", tz = "America/New_York"))
local_day <- as.integer(format(utc_time, "%d", tz = "America/New_York"))
local_hour <- as.integer(format(utc_time, "%H", tz = "America/New_York"))
aux <- cbind(local_day / 7, sin(2 * pi * local_hour / 24),
             cos(2 * pi * local_hour / 24))
weather_mu <- colMeans(hour_x, na.rm = TRUE)
weather_sd <- apply(hour_x, 2, sd, na.rm = TRUE)
scaled_weather <- sweep(sweep(hour_x, 2, weather_mu), 2, weather_sd, "/")
hour_complete <- complete.cases(hour_x)
recipients <- which(!hour_complete)
group <- paste(hourly$origin, local_month, sep = "|")
donor_pools <- split(which(hour_complete), group[hour_complete])
candidates <- matrix(NA_integer_, nrow = length(recipients), ncol = 5)

cat("尋找熱卡供體...\n")
for (i in seq_along(recipients)) {
  r <- recipients[i]
  donors <- donor_pools[[group[r]]]
  if (length(donors) < 5L) stop("同機場／月份的完整供體不足 5 筆")
  dif <- sweep(aux[donors, , drop = FALSE], 2, aux[r, ])
  distance2 <- rowSums(dif^2)
  observed_cols <- which(!is.na(hour_x[r, ]))
  for (j in observed_cols) {
    distance2 <- distance2 + (scaled_weather[donors, j] - scaled_weather[r, j])^2
  }
  candidates[i, ] <- donors[order(distance2)[1:5]]
}

fill_hotdeck <- function(seed) {
  set.seed(seed)
  chosen <- candidates[cbind(seq_along(recipients),
                             sample.int(5L, length(recipients), replace = TRUE))]
  filled <- hour_x
  for (j in seq_along(weather_vars)) {
    rows <- recipients[is.na(filled[recipients, j])]
    filled[rows, j] <- hour_x[chosen[match(rows, recipients)], j]
  }
  stopifnot(!anyNA(filled))
  x <- x_raw
  x[, weather_vars] <- filled[eligible_hour_index, , drop = FALSE]
  x
}

# ── 第 4 部分：PCA、負荷量與穩定性 ─────────────────────────────────────
# 不把機場、航空公司、月份等類別代碼放入 PCA。
# 各欄先中心化並除以標準差，避免分鐘、英里、華氏度等單位主導結果。
fit_pca <- function(x, reference = NULL, fixed_sd = NULL) {
  mu <- colMeans(x)
  sd <- if (is.null(fixed_sd)) sqrt(colMeans(sweep(x, 2, mu)^2)) else fixed_sd
  z <- sweep(sweep(x, 2, mu), 2, sd, "/")
  eig <- eigen(crossprod(z) / nrow(z), symmetric = TRUE)
  vectors <- eig$vectors
  if (!is.null(reference)) {
    signs <- sign(colSums(vectors * reference$vectors))
    signs[signs == 0] <- 1
    vectors <- sweep(vectors, 2, signs, "*")
  }
  list(n = nrow(x), mean = mu, sd = sd, eigenvalues = eig$values,
       evr = eig$values / sum(eig$values), vectors = vectors)
}
scores <- function(model, x) {
  sweep(sweep(x, 2, model$mean), 2, model$sd, "/") %*% model$vectors
}
stability <- function(reference, model, common) {
  a <- scores(reference, common)
  b <- scores(model, common)
  singular <- svd(t(reference$vectors[, 1:2]) %*% model$vectors[, 1:2])$d
  smallest <- min(singular)
  if (abs(1 - smallest) < 1e-12) smallest <- 1
  data.frame(pc1_cosine = abs(sum(reference$vectors[, 1] * model$vectors[, 1])),
             pc2_cosine = abs(sum(reference$vectors[, 2] * model$vectors[, 2])),
             pc1_score_r = abs(cor(a[, 1], b[, 1])),
             pc2_score_r = abs(cor(a[, 2], b[, 2])),
             top2_max_angle_deg = acos(pmin(1, smallest)) * 180 / pi)
}
summarize_strategy <- function(name, x, model) {
  data.frame(strategy = name, n = nrow(x),
             retained_pct_eligible = 100 * nrow(x) / nrow(eligible),
             arr_delay_mean = mean(x[, "arr_delay"]),
             arr_delay_sd = sd(x[, "arr_delay"]),
             pressure_mean = mean(x[, "pressure"]),
             pressure_sd = sd(x[, "pressure"]),
             humid_mean = mean(x[, "humid"]),
             rain_pct = 100 * mean(x[, "precip"] > 0),
             pc1_pct = 100 * model$evr[1], pc2_pct = 100 * model$evr[2],
             pc12_pct = 100 * sum(model$evr[1:2]),
             k80 = which(cumsum(model$evr) >= .8)[1])
}

model_cca <- fit_pca(x_cca)
model_mean <- fit_pca(x_mean, model_cca)
draws <- vector("list", 20)
cat("重複 20 次熱卡抽樣與 PCA...\n")
for (j in seq_along(draws)) {
  x_hot <- fill_hotdeck(20261025L + j)
  model_hot <- fit_pca(x_hot, model_cca)
  draws[[j]] <- cbind(data.frame(draw = j, seed = 20261025L + j,
                                 pc1_pct = 100 * model_hot$evr[1],
                                 pc2_pct = 100 * model_hot$evr[2]),
                      stability(model_cca, model_hot, x_cca))
  if (j == 1L) {
    x_hot_first <- x_hot
    model_hot_first <- model_hot
  }
}
write_table(do.call(rbind, draws), "hotdeck_draws")
models <- list(CCA = model_cca, MEAN = model_mean, HOTDECK = model_hot_first)
values <- list(CCA = x_cca, MEAN = x_mean, HOTDECK = x_hot_first)
summary_table <- do.call(rbind, Map(summarize_strategy, names(models), values, models))
write_table(summary_table, "strategy_summary")
stability_table <- do.call(rbind, lapply(names(models), function(name) {
  cbind(data.frame(strategy = name), stability(model_cca, models[[name]], x_cca))
}))
write_table(stability_table, "pca_stability")

# 特徵向量係數與「變數－主成分相關負荷量」分開保存，避免混淆定義。
loadings <- do.call(rbind, lapply(names(models), function(name) {
  m <- models[[name]]
  expand <- expand.grid(variable = vars, PC = seq_along(vars),
                        KEEP.OUT.ATTRS = FALSE, stringsAsFactors = FALSE)
  row <- match(expand$variable, vars)
  col <- expand$PC
  data.frame(strategy = name, expand,
             coefficient = m$vectors[cbind(row, col)],
             correlation_loading = m$vectors[cbind(row, col)] * sqrt(m$eigenvalues[col]),
             evr = m$evr[col])
}))
write_table(loadings, "pca_loadings")

# 另外固定第一份 HOTDECK 的標準差，檢查「PC1／PC2 大致穩定」是否靠重新縮放。
fixed_sd <- model_hot_first$sd
fixed_ref <- fit_pca(x_cca, fixed_sd = fixed_sd)
fixed_check <- do.call(rbind, lapply(names(models), function(name) {
  m <- fit_pca(values[[name]], fixed_ref, fixed_sd = fixed_sd)
  cbind(data.frame(strategy = name), stability(fixed_ref, m, x_cca))
}))
write_table(fixed_check, "fixed_scale_stability")

png(file.path(out, "scree.png"), width = 1450, height = 600, res = 140)
par(mfrow = c(1, 2))
cols <- c(CCA = "#237f8c", MEAN = "#da8c37", HOTDECK = "#7d63a8")
plot(1:11, 100 * model_cca$evr, type = "b", col = cols["CCA"],
     ylim = c(0, 25), xlab = "Principal component", ylab = "Explained variance (%)",
     main = "Scree plot")
for (name in c("MEAN", "HOTDECK"))
  lines(1:11, 100 * models[[name]]$evr, type = "b", col = cols[name])
legend("topright", legend = names(models), col = cols, lty = 1, pch = 1, bty = "n")
plot(1:11, 100 * cumsum(model_cca$evr), type = "b", col = cols["CCA"],
     ylim = c(0, 100), xlab = "Number retained", ylab = "Cumulative explained variance (%)",
     main = "80% criterion")
for (name in c("MEAN", "HOTDECK"))
  lines(1:11, 100 * cumsum(models[[name]]$evr), type = "b", col = cols[name])
abline(h = 80, lty = 2)
dev.off()

png(file.path(out, "loading_comparison.png"), width = 1450, height = 650, res = 140)
par(mfrow = c(1, 2), mar = c(5, 9, 3, 2))
for (pc in 1:2) {
  plot(model_cca$vectors[, pc], seq_along(vars), xlim = c(-.8, .8),
       ylim = c(length(vars), 1), yaxt = "n", xlab = "Unit eigenvector coefficient", ylab = "",
       main = paste0("PC", pc, ": sign-aligned coefficients"), pch = 16, col = cols["CCA"])
  axis(2, at = seq_along(vars), labels = vars, las = 2)
  points(model_mean$vectors[, pc], seq_along(vars), pch = 17, col = cols["MEAN"])
  points(model_hot_first$vectors[, pc], seq_along(vars), pch = 15, col = cols["HOTDECK"])
  abline(v = 0, col = "gray70")
  if (pc == 1) legend("topleft", legend = names(models), col = cols,
                      pch = c(16, 17, 15), bty = "n", cex = .75)
}
dev.off()

cat("\n三種策略摘要：\n")
print(summary_table[, c("strategy", "n", "arr_delay_mean", "pc1_pct", "pc2_pct", "k80")],
      row.names = FALSE, digits = 5)
cat("\n相對 CCA 的 PCA 穩定性：\n")
print(stability_table, row.names = FALSE, digits = 5)
cat("\n固定尺度後的穩定性：\n")
print(fixed_check, row.names = FALSE, digits = 5)
cat("\n分析完成：", out, "\n", sep = "")
