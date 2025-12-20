# Comprehensive Indicator Test Report

**Test Date:** October 1, 2024
**Total Indicators:** 141
**Passed:** 139 (98.6%)
**Failed:** 2 (1.4%)

## Summary Statistics

- Average Calculation Time: 16.51ms
- Fastest Indicator: mom (0.06ms)
- Slowest Indicator: zigzag (673.64ms)

## Passed Indicators

| # | Indicator | Calc Time (ms) | Output Columns | Incremental Update |
|---|-----------|----------------|----------------|--------------------|
| 1 | `aberration` | 9.89 | ABER_ZG_5_15, ABER_SG_5_15, ABER_XG_5_15 (+1 more) | ❌ |
| 2 | `accbands` | 0.65 | ACCBL_20, ACCBM_20, ACCBU_20 | ❌ |
| 3 | `ad` | 0.13 | AD | ❌ |
| 4 | `adosc` | 0.21 | ADOSC_3_10 | ❌ |
| 5 | `adx` | 1.36 | ADX_14, ADXR_14_2, DMP_14 (+1 more) | ❌ |
| 6 | `alligator` | 12.56 | AGj_13_8_5, AGt_13_8_5, AGl_13_8_5 | ❌ |
| 7 | `alma` | 0.23 | ALMA_9_6_0.85 | ❌ |
| 8 | `amat` | 1.34 | AMATe_LR_8_21_2, AMATe_SR_8_21_2 | ❌ |
| 9 | `anchored_vwap` | 26.50 | value | ❌ |
| 10 | `anchoredvwap` | 27.14 | value | ❌ |
| 11 | `ao` | 0.24 | AO_5_34 | ❌ |
| 12 | `aobv` | 1.95 | OBV, OBV_min_2, OBV_max_2 (+4 more) | ❌ |
| 13 | `apo` | 0.11 | APO_12_26 | ❌ |
| 14 | `aroon` | 0.19 | AROOND_14, AROONU_14, AROONOSC_14 | ❌ |
| 15 | `atr` | 0.13 | ATRr_14 | ❌ |
| 16 | `atrts` | 211.27 | ATRTSe_14_20_3.0 | ❌ |
| 17 | `bbands` | 0.46 | BBL_20_2.0_2.0, BBM_20_2.0_2.0, BBU_20_2.0_2.0 (+2 more) | ❌ |
| 18 | `bias` | 0.14 | BIAS_SMA_26 | ❌ |
| 19 | `bop` | 0.12 | BOP | ❌ |
| 20 | `brar` | 1.47 | AR_26, BR_26 | ❌ |
| 21 | `camarilla` | 159.40 | H4, H3, H2 (+5 more) | ❌ |
| 22 | `cci` | 0.14 | CCI_14_0.015 | ❌ |
| 23 | `cdldoji` | 0.39 | CDL_DOJI_10_0.1 | ❌ |
| 24 | `cdlinside` | 4.22 | CDL_INSIDE | ❌ |
| 25 | `cdlpattern` | 7.32 | CDL_2CROWS, CDL_3BLACKCROWS, CDL_3INSIDE (+59 more) | ❌ |
| 26 | `cfo` | 0.22 | CFO_9 | ❌ |
| 27 | `cg` | 1.09 | CG_10 | ❌ |
| 28 | `chandelierexit` | 1.08 | CHDLREXTl_22_22_14_2.0, CHDLREXTs_22_22_14_2.0, CHDLREXTd_22_22_14_2.0 | ❌ |
| 29 | `chop` | 0.44 | CHOP_14_1_100.0 | ❌ |
| 30 | `cksp` | 0.48 | CKSPl_10_3_20, CKSPs_10_3_20 | ❌ |
| 31 | `cmf` | 0.33 | CMF_20 | ❌ |
| 32 | `cmo` | 0.07 | CMO_14 | ❌ |
| 33 | `coppock` | 0.15 | COPC_11_14_10 | ❌ |
| 34 | `cpr` | 79.67 | TC, PIVOT, BC | ❌ |
| 35 | `cti` | 2.92 | CTI_12 | ❌ |
| 36 | `decay` | 3.53 | LDECAY_5 | ❌ |
| 37 | `dema` | 0.14 | DEMA_20 | ❌ |
| 38 | `dm` | 0.20 | DMP_14, DMN_14 | ❌ |
| 39 | `donchian` | 0.32 | DCL_20_20, DCM_20_20, DCU_20_20 | ❌ |
| 40 | `dpo` | 0.16 | DPO_20 | ❌ |
| 41 | `drawdown` | 0.29 | DD, DD_PCT, DD_LOG | ❌ |
| 42 | `efi` | 0.15 | EFI_13 | ❌ |
| 43 | `elder_ray` | 0.48 | bull_power, bear_power | ❌ |
| 44 | `elderray` | 0.34 | bull_power, bear_power | ❌ |
| 45 | `ema` | 0.07 | EMA_20 | ❌ |
| 46 | `entropy` | 0.26 | ENTP_10 | ❌ |
| 47 | `eom` | 0.49 | EOM_14_100000000 | ❌ |
| 48 | `er` | 0.22 | ER_10 | ❌ |
| 49 | `fibonaccipivot` | 151.34 | PP, R1, R2 (+4 more) | ❌ |
| 50 | `fisher` | 1.60 | FISHERT_9_1, FISHERTs_9_1 | ❌ |
| 51 | `fwma` | 4.95 | FWMA_10 | ❌ |
| 52 | `ha` | 2.66 | HA_open, HA_high, HA_low (+1 more) | ❌ |
| 53 | `heikin_ashi` | 161.38 | HA_Close, HA_Open, HA_High (+1 more) | ❌ |
| 54 | `heikinashi` | 158.08 | HA_Close, HA_Open, HA_High (+1 more) | ❌ |
| 55 | `hma` | 0.26 | HMA_20 | ❌ |
| 56 | `httrendline` | 0.17 | HT_TL | ❌ |
| 57 | `hwc` | 4.79 | HWM_1, HWL_1, HWU_1 (+2 more) | ❌ |
| 58 | `hwma` | 1.89 | HWMA_0.2_0.1_0.1 | ❌ |
| 59 | `ichimoku` | 1.26 | tenkan_sen, kijun_sen, senkou_span_a (+2 more) | ❌ |
| 60 | `inertia` | 1.04 | INERTIA_20_14 | ❌ |
| 61 | `jma` | 5.94 | JMA_7_0.0 | ❌ |
| 62 | `kama` | 1.67 | KAMA_10_2_30 | ❌ |
| 63 | `kc` | 0.36 | KCLe_20_2, KCBe_20_2, KCUe_20_2 | ❌ |
| 64 | `kdj` | 0.48 | K_9_3, D_9_3, J_9_3 | ❌ |
| 65 | `kst` | 0.51 | KST_10_15_20_30_10_10_10_15, KSTs_9 | ❌ |
| 66 | `kurtosis` | 0.17 | KURT_30 | ❌ |
| 67 | `kvo` | 1.44 | KVO_34_55_13, KVOs_34_55_13 | ❌ |
| 68 | `linreg` | 0.19 | LINREG_14 | ❌ |
| 69 | `logreturn` | 0.12 | LOGRET_1 | ❌ |
| 70 | `macd` | 0.25 | MACD_12_26_9, MACDh_12_26_9, MACDs_12_26_9 | ❌ |
| 71 | `mad` | 2.64 | MAD_30 | ❌ |
| 72 | `massi` | 0.39 | MASSI_9_25 | ❌ |
| 73 | `median` | 0.31 | MEDIAN_30 | ❌ |
| 74 | `mfi` | 0.12 | MFI_14 | ❌ |
| 75 | `midpoint` | 0.10 | MIDPOINT_14 | ❌ |
| 76 | `midprice` | 0.08 | MIDPRICE_14 | ❌ |
| 77 | `mom` | 0.06 | MOM_10 | ❌ |
| 78 | `natr` | 0.09 | NATR_14 | ❌ |
| 79 | `nvi` | 2.35 | NVI_1 | ❌ |
| 80 | `obv` | 0.09 | OBV | ❌ |
| 81 | `percentreturn` | 0.09 | PCTRET_1 | ❌ |
| 82 | `pgo` | 0.23 | PGO_14 | ❌ |
| 83 | `pivot` | 145.32 | PP, R1, R2 (+4 more) | ❌ |
| 84 | `ppo` | 0.32 | PPO_12_26_9, PPOh_12_26_9, PPOs_12_26_9 | ❌ |
| 85 | `psar` | 1.04 | PSARl_0.02_0.2, PSARs_0.02_0.2, PSARaf_0.02_0.2 (+1 more) | ❌ |
| 86 | `psl` | 0.41 | PSL_12 | ❌ |
| 87 | `pvi` | 4.27 | PVI, PVIe_255 | ❌ |
| 88 | `pvo` | 0.28 | PVO_12_26_9, PVOh_12_26_9, PVOs_12_26_9 | ❌ |
| 89 | `pvol` | 0.08 | PVOL | ❌ |
| 90 | `pvr` | 0.51 | PVR | ❌ |
| 91 | `pvt` | 0.24 | PVT | ❌ |
| 92 | `pwma` | 0.60 | PWMA_10 | ❌ |
| 93 | `qqe` | 21.80 | QQE_14_5_4.236, QQE_14_5_4.236_RSIMA, QQEl_14_5_4.236 (+1 more) | ❌ |
| 94 | `qstick` | 0.28 | QS_10 | ❌ |
| 95 | `quantile` | 0.34 | QTL_30_0.5 | ❌ |
| 96 | `renko` | 5.76 | open, high, low (+2 more) | ❌ |
| 97 | `rma` | 0.11 | RMA_14 | ❌ |
| 98 | `roc` | 0.08 | ROC_10 | ❌ |
| 99 | `rsi` | 0.07 | RSI_14 | ❌ |
| 100 | `rsx` | 2.01 | RSX_14 | ❌ |
| 101 | `rvgi` | 1.97 | RVGI_14_4, RVGIs_14_4 | ❌ |
| 102 | `rvi` | 1.37 | RVI_14 | ❌ |
| 103 | `sinwma` | 5.12 | SINWMA_14 | ❌ |
| 104 | `skew` | 0.12 | SKEW_30 | ❌ |
| 105 | `slope` | 2.24 | SLOPE_14 | ❌ |
| 106 | `sma` | 0.09 | SMA_20 | ❌ |
| 107 | `squeeze` | 1.24 | SQZ_20_2_20_1.5, SQZ_ON, SQZ_OFF (+1 more) | ❌ |
| 108 | `stc` | 6.46 | STC_10_23_50_0.5, STCmacd_10_23_50_0.5, STCstoch_10_23_50_0.5 | ❌ |
| 109 | `stdev` | 0.09 | STDEV_20 | ❌ |
| 110 | `stoch` | 0.22 | STOCHk_14_3_3, STOCHd_14_3_3, STOCHh_14_3_3 | ❌ |
| 111 | `stochrsi` | 0.42 | STOCHRSIk_14_14_3_3, STOCHRSId_14_14_3_3 | ❌ |
| 112 | `supertrend` | 5.63 | SUPERT_10_3, SUPERTd_10_3, SUPERTl_10_3 (+1 more) | ❌ |
| 113 | `support_resistance` | 173.13 | support_1, support_2, support_3 (+3 more) | ❌ |
| 114 | `supportresistance` | 150.41 | support_1, support_2, support_3 (+3 more) | ❌ |
| 115 | `swma` | 0.49 | SWMA_4 | ❌ |
| 116 | `t3` | 0.09 | T3_5_0.7 | ❌ |
| 117 | `tema` | 0.07 | TEMA_20 | ❌ |
| 118 | `thermo` | 0.63 | THERMO_20_2_0.5, THERMOma_20_2_0.5, THERMOl_20_2_0.5 (+1 more) | ❌ |
| 119 | `trima` | 0.08 | TRIMA_10 | ❌ |
| 120 | `trix` | 0.46 | TRIX_30_9, TRIXs_30_9 | ❌ |
| 121 | `truerange` | 0.11 | TRUERANGE_1 | ❌ |
| 122 | `tsi` | 0.36 | TSI_13_25_13, TSIs_13_25_13 | ❌ |
| 123 | `tsv` | 0.92 | TSV_18_10, TSVs_18_10, TSVr_18_10 | ❌ |
| 124 | `ttmtrend` | 0.62 | TTM_TRND_6 | ❌ |
| 125 | `ui` | 0.29 | UI_14 | ❌ |
| 126 | `uo` | 0.11 | UO_7_14_28 | ❌ |
| 127 | `variance` | 0.06 | VAR_20 | ❌ |
| 128 | `vhf` | 0.39 | VHF_28 | ❌ |
| 129 | `vidya` | 9.83 | VIDYA_14 | ❌ |
| 130 | `vortex` | 0.60 | VTXP_14, VTXM_14 | ❌ |
| 131 | `vp` | 2.60 | low_close, mean_close, high_close (+4 more) | ❌ |
| 132 | `vwap` | 2.87 | VWAP_D | ❌ |
| 133 | `vwma` | 0.18 | VWMA_20 | ❌ |
| 134 | `willr` | 0.10 | WILLR_14 | ❌ |
| 135 | `wma` | 0.07 | WMA_20 | ❌ |
| 136 | `zigzag` | 673.64 | ZIGZAGs_5.0%_10, ZIGZAGv_5.0%_10, ZIGZAGd_5.0%_10 | ❌ |
| 137 | `zlema` | 0.25 | ZL_EMA_20 | ❌ |
| 138 | `zlma` | 0.18 | ZL_EMA_20 | ❌ |
| 139 | `zscore` | 0.17 | ZS_30 | ❌ |

## Failed Indicators

| # | Indicator | Error |
|---|-----------|-------|
| 1 | `hybrid` | Can't instantiate abstract class HybridIndicator without an implementation for abstract methods '_in... |
| 2 | `smi` | smi() got multiple values for argument 'fast' |

## Detailed Test Results

### aberration

- **Status:** ✅ PASSED
- **Class:** `ABERRATIONIndicator`
- **Calculation Time:** 9.89ms
- **Output Columns:** `ABER_ZG_5_15`, `ABER_SG_5_15`, `ABER_XG_5_15`, `ABER_ATR_5_15`
- **Sample Values:** {
  "ABER_ZG_5_15": 25722.735371061754,
  "ABER_SG_5_15": 25734.03481025946,
  "ABER_XG_5_15": 25711.435931864045,
  "ABER_ATR_5_15": 11.299439197706922
}

### accbands

- **Status:** ✅ PASSED
- **Class:** `ACCBANDSIndicator`
- **Calculation Time:** 0.65ms
- **Output Columns:** `ACCBL_20`, `ACCBM_20`, `ACCBU_20`
- **Sample Values:** {
  "ACCBL_20": 25702.313187222833,
  "ACCBM_20": 25723.634206687908,
  "ACCBU_20": 25743.60061212147
}

### ad

- **Status:** ✅ PASSED
- **Class:** `ADIndicator`
- **Calculation Time:** 0.13ms
- **Output Columns:** `AD`
- **Sample Values:** {
  "value": 13344.471017078784
}

### adosc

- **Status:** ✅ PASSED
- **Class:** `ADOSCIndicator`
- **Calculation Time:** 0.21ms
- **Output Columns:** `ADOSC_3_10`
- **Sample Values:** {
  "value": 597.161356585626
}

### adx

- **Status:** ✅ PASSED
- **Class:** `ADXIndicator`
- **Calculation Time:** 1.36ms
- **Output Columns:** `ADX_14`, `ADXR_14_2`, `DMP_14`, `DMN_14`
- **Sample Values:** {
  "ADX_14": 13.235150046465446,
  "ADXR_14_2": 12.848251022069554,
  "DMP_14": 44.700686872074435,
  "DMN_14": 58.36163084498582
}

### alligator

- **Status:** ✅ PASSED
- **Class:** `ALLIGATORIndicator`
- **Calculation Time:** 12.56ms
- **Output Columns:** `AGj_13_8_5`, `AGt_13_8_5`, `AGl_13_8_5`
- **Sample Values:** {
  "AGj_13_8_5": 25725.05304896705,
  "AGt_13_8_5": 25726.10335292876,
  "AGl_13_8_5": 25726.265124623584
}

### alma

- **Status:** ✅ PASSED
- **Class:** `ALMAIndicator`
- **Calculation Time:** 0.23ms
- **Output Columns:** `ALMA_9_6_0.85`
- **Sample Values:** {
  "value": 25722.82239460189
}

### amat

- **Status:** ✅ PASSED
- **Class:** `AMATIndicator`
- **Calculation Time:** 1.34ms
- **Output Columns:** `AMATe_LR_8_21_2`, `AMATe_SR_8_21_2`
- **Sample Values:** {
  "AMATe_LR_8_21_2": 0.0,
  "AMATe_SR_8_21_2": 1.0
}

### anchored_vwap

- **Status:** ✅ PASSED
- **Class:** `AnchoredVWAPIndicator`
- **Calculation Time:** 26.50ms
- **Output Columns:** `value`
- **Sample Values:** {
  "value": 25779.617465254756
}

### anchoredvwap

- **Status:** ✅ PASSED
- **Class:** `AnchoredVWAPIndicator`
- **Calculation Time:** 27.14ms
- **Output Columns:** `value`
- **Sample Values:** {
  "value": 25779.617465254756
}

### ao

- **Status:** ✅ PASSED
- **Class:** `AOIndicator`
- **Calculation Time:** 0.24ms
- **Output Columns:** `AO_5_34`
- **Sample Values:** {
  "value": 7.412873989880609
}

### aobv

- **Status:** ✅ PASSED
- **Class:** `AOBVIndicator`
- **Calculation Time:** 1.95ms
- **Output Columns:** `OBV`, `OBV_min_2`, `OBV_max_2`, `OBVe_4`, `OBVe_12`, `AOBV_LR_2`, `AOBV_SR_2`
- **Sample Values:** {
  "OBV": 12441.0,
  "OBV_min_2": 11407.0,
  "OBV_max_2": 12441.0,
  "OBVe_4": 12902.152331426923,
  "OBVe_12": 14115.688226721064,
  "AOBV_LR_2": 0.0,
  "AOBV_SR_2": 1.0
}

### apo

- **Status:** ✅ PASSED
- **Class:** `APOIndicator`
- **Calculation Time:** 0.11ms
- **Output Columns:** `APO_12_26`
- **Sample Values:** {
  "value": 6.018330030128709
}

### aroon

- **Status:** ✅ PASSED
- **Class:** `AROONIndicator`
- **Calculation Time:** 0.19ms
- **Output Columns:** `AROOND_14`, `AROONU_14`, `AROONOSC_14`
- **Sample Values:** {
  "AROOND_14": 92.85714285714286,
  "AROONU_14": 7.142857142857143,
  "AROONOSC_14": -85.71428571428572
}

### atr

- **Status:** ✅ PASSED
- **Class:** `ATRIndicator`
- **Calculation Time:** 0.13ms
- **Output Columns:** `ATRr_14`
- **Sample Values:** {
  "value": 11.231555504716738
}

### atrts

- **Status:** ✅ PASSED
- **Class:** `ATRTSIndicator`
- **Calculation Time:** 211.27ms
- **Output Columns:** `ATRTSe_14_20_3.0`
- **Sample Values:** {
  "value": 25732.610958696157
}

### bbands

- **Status:** ✅ PASSED
- **Class:** `BBANDSIndicator`
- **Calculation Time:** 0.46ms
- **Output Columns:** `BBL_20_2.0_2.0`, `BBM_20_2.0_2.0`, `BBU_20_2.0_2.0`, `BBB_20_2.0_2.0`, `BBP_20_2.0_2.0`
- **Sample Values:** {
  "BBL_20_2.0_2.0": 25704.642413397258,
  "BBM_20_2.0_2.0": 25723.634206687908,
  "BBU_20_2.0_2.0": 25742.625999978558,
  "BBB_20_2.0_2.0": 0.14766026556008482,
  "BBP_20_2.0_2.0": 0.37495040792436757
}

### bias

- **Status:** ✅ PASSED
- **Class:** `BIASIndicator`
- **Calculation Time:** 0.14ms
- **Output Columns:** `BIAS_SMA_26`
- **Sample Values:** {
  "value": 1.7797247944262296e-06
}

### bop

- **Status:** ✅ PASSED
- **Class:** `BOPIndicator`
- **Calculation Time:** 0.12ms
- **Output Columns:** `BOP`
- **Sample Values:** {
  "value": 0.17112211230948263
}

### brar

- **Status:** ✅ PASSED
- **Class:** `BRARIndicator`
- **Calculation Time:** 1.47ms
- **Output Columns:** `AR_26`, `BR_26`
- **Sample Values:** {
  "AR_26": 76.63693117585397,
  "BR_26": 83.87186792381478
}

### camarilla

- **Status:** ✅ PASSED
- **Class:** `CAMARILLAIndicator`
- **Calculation Time:** 159.40ms
- **Output Columns:** `H4`, `H3`, `H2`, `H1`, `L1`, `L2`, `L3`, `L4`
- **Sample Values:** {
  "H4": null,
  "H3": null,
  "H2": null,
  "H1": null,
  "L1": null,
  "L2": null,
  "L3": null,
  "L4": null
}

### cci

- **Status:** ✅ PASSED
- **Class:** `CCIIndicator`
- **Calculation Time:** 0.14ms
- **Output Columns:** `CCI_14_0.015`
- **Sample Values:** {
  "value": -56.11624907574272
}

### cdldoji

- **Status:** ✅ PASSED
- **Class:** `CDLDOJIIndicator`
- **Calculation Time:** 0.39ms
- **Output Columns:** `CDL_DOJI_10_0.1`
- **Sample Values:** {
  "value": 0.0
}

### cdlinside

- **Status:** ✅ PASSED
- **Class:** `CDLINSIDEIndicator`
- **Calculation Time:** 4.22ms
- **Output Columns:** `CDL_INSIDE`
- **Sample Values:** {
  "value": 0.0
}

### cdlpattern

- **Status:** ✅ PASSED
- **Class:** `CDLPATTERNIndicator`
- **Calculation Time:** 7.32ms
- **Output Columns:** `CDL_2CROWS`, `CDL_3BLACKCROWS`, `CDL_3INSIDE`, `CDL_3LINESTRIKE`, `CDL_3OUTSIDE`, `CDL_3STARSINSOUTH`, `CDL_3WHITESOLDIERS`, `CDL_ABANDONEDBABY`, `CDL_ADVANCEBLOCK`, `CDL_BELTHOLD`, `CDL_BREAKAWAY`, `CDL_CLOSINGMARUBOZU`, `CDL_CONCEALBABYSWALL`, `CDL_COUNTERATTACK`, `CDL_DARKCLOUDCOVER`, `CDL_DOJI_10_0.1`, `CDL_DOJISTAR`, `CDL_DRAGONFLYDOJI`, `CDL_ENGULFING`, `CDL_EVENINGDOJISTAR`, `CDL_EVENINGSTAR`, `CDL_GAPSIDESIDEWHITE`, `CDL_GRAVESTONEDOJI`, `CDL_HAMMER`, `CDL_HANGINGMAN`, `CDL_HARAMI`, `CDL_HARAMICROSS`, `CDL_HIGHWAVE`, `CDL_HIKKAKE`, `CDL_HIKKAKEMOD`, `CDL_HOMINGPIGEON`, `CDL_IDENTICAL3CROWS`, `CDL_INNECK`, `CDL_INSIDE`, `CDL_INVERTEDHAMMER`, `CDL_KICKING`, `CDL_KICKINGBYLENGTH`, `CDL_LADDERBOTTOM`, `CDL_LONGLEGGEDDOJI`, `CDL_LONGLINE`, `CDL_MARUBOZU`, `CDL_MATCHINGLOW`, `CDL_MATHOLD`, `CDL_MORNINGDOJISTAR`, `CDL_MORNINGSTAR`, `CDL_ONNECK`, `CDL_PIERCING`, `CDL_RICKSHAWMAN`, `CDL_RISEFALL3METHODS`, `CDL_SEPARATINGLINES`, `CDL_SHOOTINGSTAR`, `CDL_SHORTLINE`, `CDL_SPINNINGTOP`, `CDL_STALLEDPATTERN`, `CDL_STICKSANDWICH`, `CDL_TAKURI`, `CDL_TASUKIGAP`, `CDL_THRUSTING`, `CDL_TRISTAR`, `CDL_UNIQUE3RIVER`, `CDL_UPSIDEGAP2CROWS`, `CDL_XSIDEGAP3METHODS`
- **Sample Values:** {
  "CDL_2CROWS": 0.0,
  "CDL_3BLACKCROWS": 0.0,
  "CDL_3INSIDE": 0.0,
  "CDL_3LINESTRIKE": 0.0,
  "CDL_3OUTSIDE": 0.0,
  "CDL_3STARSINSOUTH": 0.0,
  "CDL_3WHITESOLDIERS": 0.0,
  "CDL_ABANDONEDBABY": 0.0,
  "CDL_ADVANCEBLOCK": 0.0,
  "CDL_BELTHOLD": 0.0,
  "CDL_BREAKAWAY": 0.0,
  "CDL_CLOSINGMARUBOZU": 0.0,
  "CDL_CONCEALBABYSWALL": 0.0,
  "CDL_COUNTERATTACK": 0.0,
  "CDL_DARKCLOUDCOVER": 0.0,
  "CDL_DOJI_10_0.1": 0.0,
  "CDL_DOJISTAR": 0.0,
  "CDL_DRAGONFLYDOJI": 0.0,
  "CDL_ENGULFING": 0.0,
  "CDL_EVENINGDOJISTAR": 0.0,
  "CDL_EVENINGSTAR": 0.0,
  "CDL_GAPSIDESIDEWHITE": 0.0,
  "CDL_GRAVESTONEDOJI": 0.0,
  "CDL_HAMMER": 0.0,
  "CDL_HANGINGMAN": 0.0,
  "CDL_HARAMI": 0.0,
  "CDL_HARAMICROSS": 0.0,
  "CDL_HIGHWAVE": 0.0,
  "CDL_HIKKAKE": 0.0,
  "CDL_HIKKAKEMOD": 0.0,
  "CDL_HOMINGPIGEON": 0.0,
  "CDL_IDENTICAL3CROWS": 0.0,
  "CDL_INNECK": 0.0,
  "CDL_INSIDE": 0.0,
  "CDL_INVERTEDHAMMER": 0.0,
  "CDL_KICKING": 0.0,
  "CDL_KICKINGBYLENGTH": 0.0,
  "CDL_LADDERBOTTOM": 0.0,
  "CDL_LONGLEGGEDDOJI": 0.0,
  "CDL_LONGLINE": 0.0,
  "CDL_MARUBOZU": 0.0,
  "CDL_MATCHINGLOW": 0.0,
  "CDL_MATHOLD": 0.0,
  "CDL_MORNINGDOJISTAR": 0.0,
  "CDL_MORNINGSTAR": 0.0,
  "CDL_ONNECK": 0.0,
  "CDL_PIERCING": 0.0,
  "CDL_RICKSHAWMAN": 0.0,
  "CDL_RISEFALL3METHODS": 0.0,
  "CDL_SEPARATINGLINES": 0.0,
  "CDL_SHOOTINGSTAR": -100.0,
  "CDL_SHORTLINE": 0.0,
  "CDL_SPINNINGTOP": 0.0,
  "CDL_STALLEDPATTERN": 0.0,
  "CDL_STICKSANDWICH": 0.0,
  "CDL_TAKURI": 0.0,
  "CDL_TASUKIGAP": 0.0,
  "CDL_THRUSTING": 0.0,
  "CDL_TRISTAR": 0.0,
  "CDL_UNIQUE3RIVER": 0.0,
  "CDL_UPSIDEGAP2CROWS": 0.0,
  "CDL_XSIDEGAP3METHODS": 0.0
}

### cfo

- **Status:** ✅ PASSED
- **Class:** `CFOIndicator`
- **Calculation Time:** 0.22ms
- **Output Columns:** `CFO_9`
- **Sample Values:** {
  "value": -0.007043374042627707
}

### cg

- **Status:** ✅ PASSED
- **Class:** `CGIndicator`
- **Calculation Time:** 1.09ms
- **Output Columns:** `CG_10`
- **Sample Values:** {
  "value": -5.499840194507873
}

### chandelierexit

- **Status:** ✅ PASSED
- **Class:** `CHANDELIEREXITIndicator`
- **Calculation Time:** 1.08ms
- **Output Columns:** `CHDLREXTl_22_22_14_2.0`, `CHDLREXTs_22_22_14_2.0`, `CHDLREXTd_22_22_14_2.0`
- **Sample Values:** {
  "CHDLREXTl_22_22_14_2.0": 25717.87393513586,
  "CHDLREXTs_22_22_14_2.0": 25711.63132388441,
  "CHDLREXTd_22_22_14_2.0": 1.0
}

### chop

- **Status:** ✅ PASSED
- **Class:** `CHOPIndicator`
- **Calculation Time:** 0.44ms
- **Output Columns:** `CHOP_14_1_100.0`
- **Sample Values:** {
  "value": 57.162960272627274
}

### cksp

- **Status:** ✅ PASSED
- **Class:** `CKSPIndicator`
- **Calculation Time:** 0.48ms
- **Output Columns:** `CKSPl_10_3_20`, `CKSPs_10_3_20`
- **Sample Values:** {
  "CKSPl_10_3_20": 25708.890438485116,
  "CKSPs_10_3_20": 25726.164057655213
}

### cmf

- **Status:** ✅ PASSED
- **Class:** `CMFIndicator`
- **Calculation Time:** 0.33ms
- **Output Columns:** `CMF_20`
- **Sample Values:** {
  "value": 0.1439602083932666
}

### cmo

- **Status:** ✅ PASSED
- **Class:** `CMOIndicator`
- **Calculation Time:** 0.07ms
- **Output Columns:** `CMO_14`
- **Sample Values:** {
  "value": -3.200619309684832
}

### coppock

- **Status:** ✅ PASSED
- **Class:** `COPPOCKIndicator`
- **Calculation Time:** 0.15ms
- **Output Columns:** `COPC_11_14_10`
- **Sample Values:** {
  "value": 0.009049500471392398
}

### cpr

- **Status:** ✅ PASSED
- **Class:** `CPRIndicator`
- **Calculation Time:** 79.67ms
- **Output Columns:** `TC`, `PIVOT`, `BC`
- **Sample Values:** {
  "TC": null,
  "PIVOT": null,
  "BC": null
}

### cti

- **Status:** ✅ PASSED
- **Class:** `CTIIndicator`
- **Calculation Time:** 2.92ms
- **Output Columns:** `CTI_12`
- **Sample Values:** {
  "value": -0.27236701275507413
}

### decay

- **Status:** ✅ PASSED
- **Class:** `DECAYIndicator`
- **Calculation Time:** 3.53ms
- **Output Columns:** `LDECAY_5`
- **Sample Values:** {
  "value": 25922.156457206278
}

### dema

- **Status:** ✅ PASSED
- **Class:** `DEMAIndicator`
- **Calculation Time:** 0.14ms
- **Output Columns:** `DEMA_20`
- **Sample Values:** {
  "value": 25724.435134167285
}

### dm

- **Status:** ✅ PASSED
- **Class:** `DMIndicator`
- **Calculation Time:** 0.20ms
- **Output Columns:** `DMP_14`, `DMN_14`
- **Sample Values:** {
  "DMP_14": 44.700686872074435,
  "DMN_14": 58.36163084498582
}

### donchian

- **Status:** ✅ PASSED
- **Class:** `DONCHIANIndicator`
- **Calculation Time:** 0.32ms
- **Output Columns:** `DCL_20_20`, `DCM_20_20`, `DCU_20_20`
- **Sample Values:** {
  "DCL_20_20": 25691.947148724157,
  "DCM_20_20": 25716.142097434727,
  "DCU_20_20": 25740.337046145294
}

### dpo

- **Status:** ✅ PASSED
- **Class:** `DPOIndicator`
- **Calculation Time:** 0.16ms
- **Output Columns:** `DPO_20`
- **Sample Values:** {
  "value": null
}

### drawdown

- **Status:** ✅ PASSED
- **Class:** `DRAWDOWNIndicator`
- **Calculation Time:** 0.29ms
- **Output Columns:** `DD`, `DD_PCT`, `DD_LOG`
- **Sample Values:** {
  "DD": 237.4720825260556,
  "DD_PCT": 0.00914889895727733,
  "DD_LOG": 0.009191007159234488
}

### efi

- **Status:** ✅ PASSED
- **Class:** `EFIIndicator`
- **Calculation Time:** 0.15ms
- **Output Columns:** `EFI_13`
- **Sample Values:** {
  "value": -1801.116848147927
}

### elder_ray

- **Status:** ✅ PASSED
- **Class:** `ElderRayIndicator`
- **Calculation Time:** 0.48ms
- **Output Columns:** `bull_power`, `bear_power`
- **Sample Values:** {
  "bull_power": 0.9237538555025822,
  "bear_power": -5.132369651899353
}

### elderray

- **Status:** ✅ PASSED
- **Class:** `ElderRayIndicator`
- **Calculation Time:** 0.34ms
- **Output Columns:** `bull_power`, `bear_power`
- **Sample Values:** {
  "bull_power": 0.9237538555025822,
  "bear_power": -5.132369651899353
}

### ema

- **Status:** ✅ PASSED
- **Class:** `EMAIndicator`
- **Calculation Time:** 0.07ms
- **Output Columns:** `EMA_20`
- **Sample Values:** {
  "value": 25722.113341988632
}

### entropy

- **Status:** ✅ PASSED
- **Class:** `ENTROPYIndicator`
- **Calculation Time:** 0.26ms
- **Output Columns:** `ENTP_10`
- **Sample Values:** {
  "value": 3.3217994509777253
}

### eom

- **Status:** ✅ PASSED
- **Class:** `EOMIndicator`
- **Calculation Time:** 0.49ms
- **Output Columns:** `EOM_14_100000000`
- **Sample Values:** {
  "value": -1328354.2514479856
}

### er

- **Status:** ✅ PASSED
- **Class:** `ERIndicator`
- **Calculation Time:** 0.22ms
- **Output Columns:** `ER_10`
- **Sample Values:** {
  "value": 0.07662321989716299
}

### fibonaccipivot

- **Status:** ✅ PASSED
- **Class:** `FIBONACCIPIVOTIndicator`
- **Calculation Time:** 151.34ms
- **Output Columns:** `PP`, `R1`, `R2`, `R3`, `S1`, `S2`, `S3`
- **Sample Values:** {
  "PP": null,
  "R1": null,
  "R2": null,
  "R3": null,
  "S1": null,
  "S2": null,
  "S3": null
}

### fisher

- **Status:** ✅ PASSED
- **Class:** `FISHERIndicator`
- **Calculation Time:** 1.60ms
- **Output Columns:** `FISHERT_9_1`, `FISHERTs_9_1`
- **Sample Values:** {
  "FISHERT_9_1": -0.5922709235054884,
  "FISHERTs_9_1": -0.3935387246925165
}

### fwma

- **Status:** ✅ PASSED
- **Class:** `FWMAIndicator`
- **Calculation Time:** 4.95ms
- **Output Columns:** `FWMA_10`
- **Sample Values:** {
  "value": 25720.669588703662
}

### ha

- **Status:** ✅ PASSED
- **Class:** `HAIndicator`
- **Calculation Time:** 2.66ms
- **Output Columns:** `HA_open`, `HA_high`, `HA_low`, `HA_close`
- **Sample Values:** {
  "HA_open": 25719.48350263945,
  "HA_high": 25723.904161540755,
  "HA_low": 25717.848038033353,
  "HA_close": 25719.621153071952
}

### heikin_ashi

- **Status:** ✅ PASSED
- **Class:** `HeikinAshiIndicator`
- **Calculation Time:** 161.38ms
- **Output Columns:** `HA_Close`, `HA_Open`, `HA_High`, `HA_Low`
- **Sample Values:** {
  "HA_Close": 25719.621153071952,
  "HA_Open": 25719.48350263945,
  "HA_High": 25723.904161540755,
  "HA_Low": 25717.848038033353
}

### heikinashi

- **Status:** ✅ PASSED
- **Class:** `HeikinAshiIndicator`
- **Calculation Time:** 158.08ms
- **Output Columns:** `HA_Close`, `HA_Open`, `HA_High`, `HA_Low`
- **Sample Values:** {
  "HA_Close": 25719.621153071952,
  "HA_Open": 25719.48350263945,
  "HA_High": 25723.904161540755,
  "HA_Low": 25717.848038033353
}

### hma

- **Status:** ✅ PASSED
- **Class:** `HMAIndicator`
- **Calculation Time:** 0.26ms
- **Output Columns:** `HMA_20`
- **Sample Values:** {
  "value": 25724.92682930609
}

### httrendline

- **Status:** ✅ PASSED
- **Class:** `HTTRENDLINEIndicator`
- **Calculation Time:** 0.17ms
- **Output Columns:** `HT_TL`
- **Sample Values:** {
  "value": 25726.657926670123
}

### hwc

- **Status:** ✅ PASSED
- **Class:** `HWCIndicator`
- **Calculation Time:** 4.79ms
- **Output Columns:** `HWM_1`, `HWL_1`, `HWU_1`, `HWW_1`, `HWPCT_1`
- **Sample Values:** {
  "HWM_1": 25724.932934887387,
  "HWL_1": 25713.516689634504,
  "HWU_1": 25736.34918014027,
  "HWW_1": 22.832490505767055,
  "HWPCT_1": 0.23508977456872127
}

### hwma

- **Status:** ✅ PASSED
- **Class:** `HWMAIndicator`
- **Calculation Time:** 1.89ms
- **Output Columns:** `HWMA_0.2_0.1_0.1`
- **Sample Values:** {
  "value": 25724.932934887387
}

### hybrid

- **Status:** ❌ FAILED
- **Class:** `HybridIndicator`
- **Calculation Time:** 0.00ms
- **Error:** `Can't instantiate abstract class HybridIndicator without an implementation for abstract methods '_initialize_state_from_dataframe', 'calculate_bulk', 'update'`

### ichimoku

- **Status:** ✅ PASSED
- **Class:** `IchimokuIndicator`
- **Calculation Time:** 1.26ms
- **Output Columns:** `tenkan_sen`, `kijun_sen`, `senkou_span_a`, `senkou_span_b`, `chikou_span`
- **Sample Values:** {
  "tenkan_sen": 25723.36146795456,
  "kijun_sen": 25714.752629510134,
  "senkou_span_a": 25714.66110583574,
  "senkou_span_b": 25743.680304895697,
  "chikou_span": null
}

### inertia

- **Status:** ✅ PASSED
- **Class:** `INERTIAIndicator`
- **Calculation Time:** 1.04ms
- **Output Columns:** `INERTIA_20_14`
- **Sample Values:** {
  "value": 52.346191727628295
}

### jma

- **Status:** ✅ PASSED
- **Class:** `JMAIndicator`
- **Calculation Time:** 5.94ms
- **Output Columns:** `JMA_7_0.0`
- **Sample Values:** {
  "value": 25723.333449969927
}

### kama

- **Status:** ✅ PASSED
- **Class:** `KAMAIndicator`
- **Calculation Time:** 1.67ms
- **Output Columns:** `KAMA_10_2_30`
- **Sample Values:** {
  "value": 25723.043862199498
}

### kc

- **Status:** ✅ PASSED
- **Class:** `KCIndicator`
- **Calculation Time:** 0.36ms
- **Output Columns:** `KCLe_20_2`, `KCBe_20_2`, `KCUe_20_2`
- **Sample Values:** {
  "KCLe_20_2": 25700.206949291824,
  "KCBe_20_2": 25722.113341988632,
  "KCUe_20_2": 25744.01973468544
}

### kdj

- **Status:** ✅ PASSED
- **Class:** `KDJIndicator`
- **Calculation Time:** 0.48ms
- **Output Columns:** `K_9_3`, `D_9_3`, `J_9_3`
- **Sample Values:** {
  "K_9_3": 40.34362894908748,
  "D_9_3": 48.93939536394149,
  "J_9_3": 23.152096119379465
}

### kst

- **Status:** ✅ PASSED
- **Class:** `KSTIndicator`
- **Calculation Time:** 0.51ms
- **Output Columns:** `KST_10_15_20_30_10_10_10_15`, `KSTs_9`
- **Sample Values:** {
  "KST_10_15_20_30_10_10_10_15": 45.65340001499688,
  "KSTs_9": 48.461618553831926
}

### kurtosis

- **Status:** ✅ PASSED
- **Class:** `KURTOSISIndicator`
- **Calculation Time:** 0.17ms
- **Output Columns:** `KURT_30`
- **Sample Values:** {
  "value": -0.9162682163692072
}

### kvo

- **Status:** ✅ PASSED
- **Class:** `KVOIndicator`
- **Calculation Time:** 1.44ms
- **Output Columns:** `KVO_34_55_13`, `KVOs_34_55_13`
- **Sample Values:** {
  "KVO_34_55_13": -21.61005735126949,
  "KVOs_34_55_13": 18.27348026070395
}

### linreg

- **Status:** ✅ PASSED
- **Class:** `LINREGIndicator`
- **Calculation Time:** 0.19ms
- **Output Columns:** `LINREG_14`
- **Sample Values:** {
  "value": 25722.240706413882
}

### logreturn

- **Status:** ✅ PASSED
- **Class:** `LOGRETURNIndicator`
- **Calculation Time:** 0.12ms
- **Output Columns:** `LOGRET_1`
- **Sample Values:** {
  "value": 0.00014671249560173374
}

### macd

- **Status:** ✅ PASSED
- **Class:** `MACDIndicator`
- **Calculation Time:** 0.25ms
- **Output Columns:** `MACD_12_26_9`, `MACDh_12_26_9`, `MACDs_12_26_9`
- **Sample Values:** {
  "MACD_12_26_9": 1.434163132984395,
  "MACDh_12_26_9": -0.9165314470261987,
  "MACDs_12_26_9": 2.3506945800105936
}

### mad

- **Status:** ✅ PASSED
- **Class:** `MADIndicator`
- **Calculation Time:** 2.64ms
- **Output Columns:** `MAD_30`
- **Sample Values:** {
  "value": 11.050985226045425
}

### massi

- **Status:** ✅ PASSED
- **Class:** `MASSIIndicator`
- **Calculation Time:** 0.39ms
- **Output Columns:** `MASSI_9_25`
- **Sample Values:** {
  "value": 24.400205298380484
}

### median

- **Status:** ✅ PASSED
- **Class:** `MEDIANIndicator`
- **Calculation Time:** 0.31ms
- **Output Columns:** `MEDIAN_30`
- **Sample Values:** {
  "value": 25718.88051533189
}

### mfi

- **Status:** ✅ PASSED
- **Class:** `MFIIndicator`
- **Calculation Time:** 0.12ms
- **Output Columns:** `MFI_14`
- **Sample Values:** {
  "value": 30.523176331774142
}

### midpoint

- **Status:** ✅ PASSED
- **Class:** `MIDPOINTIndicator`
- **Calculation Time:** 0.10ms
- **Output Columns:** `MIDPOINT_14`
- **Sample Values:** {
  "value": 25726.126111299935
}

### midprice

- **Status:** ✅ PASSED
- **Class:** `MIDPRICEIndicator`
- **Calculation Time:** 0.08ms
- **Output Columns:** `MIDPRICE_14`
- **Sample Values:** {
  "value": 25724.10009489835
}

### mom

- **Status:** ✅ PASSED
- **Class:** `MOMIndicator`
- **Calculation Time:** 0.06ms
- **Output Columns:** `MOM_10`
- **Sample Values:** {
  "value": -3.8155715121647518
}

### natr

- **Status:** ✅ PASSED
- **Class:** `NATRIndicator`
- **Calculation Time:** 0.09ms
- **Output Columns:** `NATR_14`
- **Sample Values:** {
  "value": 0.0436704615219389
}

### nvi

- **Status:** ✅ PASSED
- **Class:** `NVIIndicator`
- **Calculation Time:** 2.35ms
- **Output Columns:** `NVI_1`
- **Sample Values:** {
  "value": 999.8414162741713
}

### obv

- **Status:** ✅ PASSED
- **Class:** `OBVIndicator`
- **Calculation Time:** 0.09ms
- **Output Columns:** `OBV`
- **Sample Values:** {
  "value": 12441.0
}

### percentreturn

- **Status:** ✅ PASSED
- **Class:** `PERCENTRETURNIndicator`
- **Calculation Time:** 0.09ms
- **Output Columns:** `PCTRET_1`
- **Sample Values:** {
  "value": 0.0001467232584062561
}

### pgo

- **Status:** ✅ PASSED
- **Class:** `PGOIndicator`
- **Calculation Time:** 0.23ms
- **Output Columns:** `PGO_14`
- **Sample Values:** {
  "value": -0.5362669228180144
}

### pivot

- **Status:** ✅ PASSED
- **Class:** `PIVOTIndicator`
- **Calculation Time:** 145.32ms
- **Output Columns:** `PP`, `R1`, `R2`, `R3`, `S1`, `S2`, `S3`
- **Sample Values:** {
  "PP": null,
  "R1": null,
  "R2": null,
  "R3": null,
  "S1": null,
  "S2": null,
  "S3": null
}

### ppo

- **Status:** ✅ PASSED
- **Class:** `PPOIndicator`
- **Calculation Time:** 0.32ms
- **Output Columns:** `PPO_12_26_9`, `PPOh_12_26_9`, `PPOs_12_26_9`
- **Sample Values:** {
  "PPO_12_26_9": 0.023400473571959457,
  "PPOh_12_26_9": -0.005893200394742497,
  "PPOs_12_26_9": 0.029293673966701954
}

### psar

- **Status:** ✅ PASSED
- **Class:** `PSARIndicator`
- **Calculation Time:** 1.04ms
- **Output Columns:** `PSARl_0.02_0.2`, `PSARs_0.02_0.2`, `PSARaf_0.02_0.2`, `PSARr_0.02_0.2`
- **Sample Values:** {
  "PSARl_0.02_0.2": null,
  "PSARs_0.02_0.2": 25738.495394556194,
  "PSARaf_0.02_0.2": 0.04,
  "PSARr_0.02_0.2": 0.0
}

### psl

- **Status:** ✅ PASSED
- **Class:** `PSLIndicator`
- **Calculation Time:** 0.41ms
- **Output Columns:** `PSL_12`
- **Sample Values:** {
  "value": 50.0
}

### pvi

- **Status:** ✅ PASSED
- **Class:** `PVIIndicator`
- **Calculation Time:** 4.27ms
- **Output Columns:** `PVI`, `PVIe_255`
- **Sample Values:** {
  "PVI": 100.0,
  "PVIe_255": 99.99791358058062
}

### pvo

- **Status:** ✅ PASSED
- **Class:** `PVOIndicator`
- **Calculation Time:** 0.28ms
- **Output Columns:** `PVO_12_26_9`, `PVOh_12_26_9`, `PVOs_12_26_9`
- **Sample Values:** {
  "PVO_12_26_9": 0.1695097857212305,
  "PVOh_12_26_9": -1.277581948579956,
  "PVOs_12_26_9": 1.4470917343011864
}

### pvol

- **Status:** ✅ PASSED
- **Class:** `PVOLIndicator`
- **Calculation Time:** 0.08ms
- **Output Columns:** `PVOL`
- **Sample Values:** {
  "value": 26593326.44341948
}

### pvr

- **Status:** ✅ PASSED
- **Class:** `PVRIndicator`
- **Calculation Time:** 0.51ms
- **Output Columns:** `PVR`
- **Sample Values:** {
  "value": 2.0
}

### pvt

- **Status:** ✅ PASSED
- **Class:** `PVTIndicator`
- **Calculation Time:** 0.24ms
- **Output Columns:** `PVT`
- **Sample Values:** {
  "value": 127.31124282485546
}

### pwma

- **Status:** ✅ PASSED
- **Class:** `PWMAIndicator`
- **Calculation Time:** 0.60ms
- **Output Columns:** `PWMA_10`
- **Sample Values:** {
  "value": 25729.928401812154
}

### qqe

- **Status:** ✅ PASSED
- **Class:** `QQEIndicator`
- **Calculation Time:** 21.80ms
- **Output Columns:** `QQE_14_5_4.236`, `QQE_14_5_4.236_RSIMA`, `QQEl_14_5_4.236`, `QQEs_14_5_4.236`
- **Sample Values:** {
  "QQE_14_5_4.236": 48.75520745283656,
  "QQE_14_5_4.236_RSIMA": 49.75940752153984,
  "QQEl_14_5_4.236": 48.75520745283656,
  "QQEs_14_5_4.236": null
}

### qstick

- **Status:** ✅ PASSED
- **Class:** `QSTICKIndicator`
- **Calculation Time:** 0.28ms
- **Output Columns:** `QS_10`
- **Sample Values:** {
  "value": -0.3943203769813408
}

### quantile

- **Status:** ✅ PASSED
- **Class:** `QUANTILEIndicator`
- **Calculation Time:** 0.34ms
- **Output Columns:** `QTL_30_0.5`
- **Sample Values:** {
  "value": 25718.88051533189
}

### renko

- **Status:** ✅ PASSED
- **Class:** `RenkoIndicator`
- **Calculation Time:** 5.76ms
- **Output Columns:** `open`, `high`, `low`, `close`, `direction`
- **Sample Values:** {
  "open": 25724.967141530113,
  "high": 25734.967141530113,
  "low": 25724.967141530113,
  "close": 25734.967141530113,
  "direction": 1.0
}

### rma

- **Status:** ✅ PASSED
- **Class:** `RMAIndicator`
- **Calculation Time:** 0.11ms
- **Output Columns:** `RMA_14`
- **Sample Values:** {
  "value": 25721.58449166035
}

### roc

- **Status:** ✅ PASSED
- **Class:** `ROCIndicator`
- **Calculation Time:** 0.08ms
- **Output Columns:** `ROC_10`
- **Sample Values:** {
  "value": -0.014833479845222097
}

### rsi

- **Status:** ✅ PASSED
- **Class:** `RSIIndicator`
- **Calculation Time:** 0.07ms
- **Output Columns:** `RSI_14`
- **Sample Values:** {
  "value": 48.39969034515759
}

### rsx

- **Status:** ✅ PASSED
- **Class:** `RSXIndicator`
- **Calculation Time:** 2.01ms
- **Output Columns:** `RSX_14`
- **Sample Values:** {
  "value": 49.789683733316004
}

### rvgi

- **Status:** ✅ PASSED
- **Class:** `RVGIIndicator`
- **Calculation Time:** 1.97ms
- **Output Columns:** `RVGI_14_4`, `RVGIs_14_4`
- **Sample Values:** {
  "RVGI_14_4": -0.10884007896749225,
  "RVGIs_14_4": -0.037618573455697815
}

### rvi

- **Status:** ✅ PASSED
- **Class:** `RVIIndicator`
- **Calculation Time:** 1.37ms
- **Output Columns:** `RVI_14`
- **Sample Values:** {
  "value": 51.23843788674343
}

### sinwma

- **Status:** ✅ PASSED
- **Class:** `SINWMAIndicator`
- **Calculation Time:** 5.12ms
- **Output Columns:** `SINWMA_14`
- **Sample Values:** {
  "value": 25725.801935704294
}

### skew

- **Status:** ✅ PASSED
- **Class:** `SKEWIndicator`
- **Calculation Time:** 0.12ms
- **Output Columns:** `SKEW_30`
- **Sample Values:** {
  "value": -0.31320145842285796
}

### slope

- **Status:** ✅ PASSED
- **Class:** `SLOPEIndicator`
- **Calculation Time:** 2.24ms
- **Output Columns:** `SLOPE_14`
- **Sample Values:** {
  "value": -1.226078878275595
}

### sma

- **Status:** ✅ PASSED
- **Class:** `SMAIndicator`
- **Calculation Time:** 0.09ms
- **Output Columns:** `SMA_20`
- **Sample Values:** {
  "value": 25723.634206687908
}

### smi

- **Status:** ❌ FAILED
- **Class:** `SMIIndicator`
- **Calculation Time:** 0.00ms
- **Error:** `smi() got multiple values for argument 'fast'`

### squeeze

- **Status:** ✅ PASSED
- **Class:** `SQUEEZEIndicator`
- **Calculation Time:** 1.24ms
- **Output Columns:** `SQZ_20_2_20_1.5`, `SQZ_ON`, `SQZ_OFF`, `SQZ_NO`
- **Sample Values:** {
  "SQZ_20_2_20_1.5": -2.124468817130643,
  "SQZ_ON": 0.0,
  "SQZ_OFF": 1.0,
  "SQZ_NO": 0.0
}

### stc

- **Status:** ✅ PASSED
- **Class:** `STCIndicator`
- **Calculation Time:** 6.46ms
- **Output Columns:** `STC_10_23_50_0.5`, `STCmacd_10_23_50_0.5`, `STCstoch_10_23_50_0.5`
- **Sample Values:** {
  "STC_10_23_50_0.5": 0.0,
  "STCmacd_10_23_50_0.5": -3.931497563247831,
  "STCstoch_10_23_50_0.5": 0.0
}

### stdev

- **Status:** ✅ PASSED
- **Class:** `STDEVIndicator`
- **Calculation Time:** 0.09ms
- **Output Columns:** `STDEV_20`
- **Sample Values:** {
  "value": 9.495896646483905
}

### stoch

- **Status:** ✅ PASSED
- **Class:** `STOCHIndicator`
- **Calculation Time:** 0.22ms
- **Output Columns:** `STOCHk_14_3_3`, `STOCHd_14_3_3`, `STOCHh_14_3_3`
- **Sample Values:** {
  "STOCHk_14_3_3": 27.5772372313139,
  "STOCHd_14_3_3": 39.34496559178479,
  "STOCHh_14_3_3": -11.76772836047089
}

### stochrsi

- **Status:** ✅ PASSED
- **Class:** `STOCHRSIIndicator`
- **Calculation Time:** 0.42ms
- **Output Columns:** `STOCHRSIk_14_14_3_3`, `STOCHRSId_14_14_3_3`
- **Sample Values:** {
  "STOCHRSIk_14_14_3_3": 5.977233527183382,
  "STOCHRSId_14_14_3_3": 18.784234599642577
}

### supertrend

- **Status:** ✅ PASSED
- **Class:** `SUPERTRENDIndicator`
- **Calculation Time:** 5.63ms
- **Output Columns:** `SUPERT_10_3`, `SUPERTd_10_3`, `SUPERTl_10_3`, `SUPERTs_10_3`
- **Sample Values:** {
  "SUPERT_10_3": 25705.022072350133,
  "SUPERTd_10_3": 1.0,
  "SUPERTl_10_3": 25705.022072350133,
  "SUPERTs_10_3": null
}

### support_resistance

- **Status:** ✅ PASSED
- **Class:** `SupportResistanceIndicator`
- **Calculation Time:** 173.13ms
- **Output Columns:** `support_1`, `support_2`, `support_3`, `resistance_1`, `resistance_2`, `resistance_3`
- **Sample Values:** {
  "support_1": null,
  "support_2": null,
  "support_3": null,
  "resistance_1": null,
  "resistance_2": null,
  "resistance_3": null
}

### supportresistance

- **Status:** ✅ PASSED
- **Class:** `SupportResistanceIndicator`
- **Calculation Time:** 150.41ms
- **Output Columns:** `support_1`, `support_2`, `support_3`, `resistance_1`, `resistance_2`, `resistance_3`
- **Sample Values:** {
  "support_1": null,
  "support_2": null,
  "support_3": null,
  "resistance_1": null,
  "resistance_2": null,
  "resistance_3": null
}

### swma

- **Status:** ✅ PASSED
- **Class:** `SWMAIndicator`
- **Calculation Time:** 0.49ms
- **Output Columns:** `SWMA_4`
- **Sample Values:** {
  "value": 25719.592943064992
}

### t3

- **Status:** ✅ PASSED
- **Class:** `T3Indicator`
- **Calculation Time:** 0.09ms
- **Output Columns:** `T3_5_0.7`
- **Sample Values:** {
  "value": 25724.335884687975
}

### tema

- **Status:** ✅ PASSED
- **Class:** `TEMAIndicator`
- **Calculation Time:** 0.07ms
- **Output Columns:** `TEMA_20`
- **Sample Values:** {
  "value": 25726.072851655637
}

### thermo

- **Status:** ✅ PASSED
- **Class:** `THERMOIndicator`
- **Calculation Time:** 0.63ms
- **Output Columns:** `THERMO_20_2_0.5`, `THERMOma_20_2_0.5`, `THERMOl_20_2_0.5`, `THERMOs_20_2_0.5`
- **Sample Values:** {
  "THERMO_20_2_0.5": 9.984894381948834,
  "THERMOma_20_2_0.5": 9.08139595609353,
  "THERMOl_20_2_0.5": 1.0,
  "THERMOs_20_2_0.5": 1.0
}

### trima

- **Status:** ✅ PASSED
- **Class:** `TRIMAIndicator`
- **Calculation Time:** 0.08ms
- **Output Columns:** `TRIMA_10`
- **Sample Values:** {
  "value": 25726.969582509104
}

### trix

- **Status:** ✅ PASSED
- **Class:** `TRIXIndicator`
- **Calculation Time:** 0.46ms
- **Output Columns:** `TRIX_30_9`, `TRIXs_30_9`
- **Sample Values:** {
  "TRIX_30_9": -0.002415697913604742,
  "TRIXs_30_9": -0.0031081550443734507
}

### truerange

- **Status:** ✅ PASSED
- **Class:** `TRUERANGEIndicator`
- **Calculation Time:** 0.11ms
- **Output Columns:** `TRUERANGE_1`
- **Sample Values:** {
  "value": 8.792791790856427
}

### tsi

- **Status:** ✅ PASSED
- **Class:** `TSIIndicator`
- **Calculation Time:** 0.36ms
- **Output Columns:** `TSI_13_25_13`, `TSIs_13_25_13`
- **Sample Values:** {
  "TSI_13_25_13": 3.1182670203150074,
  "TSIs_13_25_13": 3.7330281249778774
}

### tsv

- **Status:** ✅ PASSED
- **Class:** `TSVIndicator`
- **Calculation Time:** 0.92ms
- **Output Columns:** `TSV_18_10`, `TSVs_18_10`, `TSVr_18_10`
- **Sample Values:** {
  "TSV_18_10": 5881.8602315446515,
  "TSVs_18_10": 13664.171732048548,
  "TSVr_18_10": 0.43045859982490403
}

### ttmtrend

- **Status:** ✅ PASSED
- **Class:** `TTMTRENDIndicator`
- **Calculation Time:** 0.62ms
- **Output Columns:** `TTM_TRND_6`
- **Sample Values:** {
  "TTM_TRND_6": -1.0
}

### ui

- **Status:** ✅ PASSED
- **Class:** `UIIndicator`
- **Calculation Time:** 0.29ms
- **Output Columns:** `UI_14`
- **Sample Values:** {
  "value": 0.04998131359030515
}

### uo

- **Status:** ✅ PASSED
- **Class:** `UOIndicator`
- **Calculation Time:** 0.11ms
- **Output Columns:** `UO_7_14_28`
- **Sample Values:** {
  "value": 55.13871944238645
}

### variance

- **Status:** ✅ PASSED
- **Class:** `VARIANCEIndicator`
- **Calculation Time:** 0.06ms
- **Output Columns:** `VAR_20`
- **Sample Values:** {
  "value": 90.17205312070426
}

### vhf

- **Status:** ✅ PASSED
- **Class:** `VHFIndicator`
- **Calculation Time:** 0.39ms
- **Output Columns:** `VHF_28`
- **Sample Values:** {
  "value": 0.23392770078928116
}

### vidya

- **Status:** ✅ PASSED
- **Class:** `VIDYAIndicator`
- **Calculation Time:** 9.83ms
- **Output Columns:** `VIDYA_14`
- **Sample Values:** {
  "value": 25731.168586586322
}

### vortex

- **Status:** ✅ PASSED
- **Class:** `VORTEXIndicator`
- **Calculation Time:** 0.60ms
- **Output Columns:** `VTXP_14`, `VTXM_14`
- **Sample Values:** {
  "VTXP_14": 0.7123089577793937,
  "VTXM_14": 1.0527841131556641
}

### vp

- **Status:** ✅ PASSED
- **Class:** `VPIndicator`
- **Calculation Time:** 2.60ms
- **Output Columns:** `low_close`, `mean_close`, `high_close`, `pos_volume`, `neg_volume`, `neut_volume`, `total_volume`
- **Sample Values:** {
  "low_close": 25692.044237955506,
  "mean_close": 25717.23236785344,
  "high_close": 25749.32169104923,
  "pos_volume": 42567.0,
  "neg_volume": 40290.0,
  "neut_volume": 0.0,
  "total_volume": 82857.0
}

### vwap

- **Status:** ✅ PASSED
- **Class:** `VWAPIndicator`
- **Calculation Time:** 2.87ms
- **Output Columns:** `VWAP_D`
- **Sample Values:** {
  "value": 25779.617465254778
}

### vwma

- **Status:** ✅ PASSED
- **Class:** `VWMAIndicator`
- **Calculation Time:** 0.18ms
- **Output Columns:** `VWMA_20`
- **Sample Values:** {
  "value": 25723.47716993882
}

### willr

- **Status:** ✅ PASSED
- **Class:** `WILLRIndicator`
- **Calculation Time:** 0.10ms
- **Output Columns:** `WILLR_14`
- **Sample Values:** {
  "value": -66.06126710204832
}

### wma

- **Status:** ✅ PASSED
- **Class:** `WMAIndicator`
- **Calculation Time:** 0.07ms
- **Output Columns:** `WMA_20`
- **Sample Values:** {
  "value": 25724.803015418616
}

### zigzag

- **Status:** ✅ PASSED
- **Class:** `ZIGZAGIndicator`
- **Calculation Time:** 673.64ms
- **Output Columns:** `ZIGZAGs_5.0%_10`, `ZIGZAGv_5.0%_10`, `ZIGZAGd_5.0%_10`
- **Sample Values:** {
  "ZIGZAGs_5.0%_10": null,
  "ZIGZAGv_5.0%_10": null,
  "ZIGZAGd_5.0%_10": null
}

### zlema

- **Status:** ✅ PASSED
- **Class:** `ZLEMAIndicator`
- **Calculation Time:** 0.25ms
- **Output Columns:** `ZL_EMA_20`
- **Sample Values:** {
  "value": 25724.71606166974
}

### zlma

- **Status:** ✅ PASSED
- **Class:** `ZLMAIndicator`
- **Calculation Time:** 0.18ms
- **Output Columns:** `ZL_EMA_20`
- **Sample Values:** {
  "value": 25724.71606166974
}

### zscore

- **Status:** ✅ PASSED
- **Class:** `ZSCOREIndicator`
- **Calculation Time:** 0.17ms
- **Output Columns:** `ZS_30`
- **Sample Values:** {
  "value": 0.13164059471055295
}

