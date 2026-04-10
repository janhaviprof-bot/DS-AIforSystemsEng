# 03_statistical_comparison.py
# Statistical Comparison of Quality Control Scores Across Prompts
# Tim Fraser

# This script demonstrates how to use t-test and ANOVA to compare quality control
# scores for reports generated from different prompts. Students learn to perform
# statistical hypothesis testing to determine if prompt differences are significant.

# 0. Setup #################################

## 0.1 Import Packages #################################

# If you haven't already, install required packages:
# !pip install pandas
# !pip install scipy
# !pip install pingouin

import pandas as pd
from scipy.stats import bartlett
import pingouin as pg

## 0.2 Load Quality Control Scores #################################

# Load pre-computed quality control scores for reports from 3 different prompts
# Each prompt generated 30 reports, and each report was evaluated on multiple criteria
scores = pd.read_csv("09_text_analysis/data/prompt_comparison_scores.csv")

# View the data structure
print("📊 Quality Control Scores Dataset:")
print(scores.head())
print(f"\nShape: {scores.shape}")
print(f"Columns: {list(scores.columns)}\n")

# 1. Descriptive Statistics #################################

## 1.1 Summary Statistics by Prompt #################################

# Calculate mean overall scores by prompt
# This gives us a first look at whether prompts differ in quality
summary_stats = scores.groupby('prompt_id').agg({
    'overall_score': ['mean', 'std'],
    'formality': 'mean',
    'succinctness': 'mean',
    'clarity': 'mean'
}).round(2)

print("📈 Summary Statistics by Prompt:")
print(summary_stats)
print()

# Overall mean across all prompts
overall_mean = scores['overall_score'].mean()
print(f"📊 Overall Mean Score (all prompts): {overall_mean:.2f}\n")

## 1.2 Visual Inspection #################################

# Calculate means and standard deviations for each prompt
# This helps us see if there are obvious differences between prompts
for prompt in ['A', 'B', 'C']:
    prompt_scores = scores.query(f'prompt_id == "{prompt}"')['overall_score']
    print(f"📊 Prompt {prompt}: Mean = {prompt_scores.mean():.2f}, SD = {prompt_scores.std():.2f}")
print()

# 2. Testing Assumptions #################################

## 2.1 Homogeneity of Variance (Bartlett's Test) #################################

# Before running ANOVA, we need to check if the variances are equal across groups
# Bartlett's test checks whether the variances of our 3 groups are significantly different

# Extract the overall_score vector for each of the 3 prompts
a = scores.query('prompt_id == "A"')['overall_score']
b = scores.query('prompt_id == "B"')['overall_score']
c = scores.query('prompt_id == "C"')['overall_score']

# Perform Bartlett's test for homogeneity of variances
b_stat, b_p_value = bartlett(a, b, c)

print("🔍 Bartlett's Test for Homogeneity of Variance:")
print(f"   Bartlett's test statistic: {b_stat:.4f}")
print(f"   p-value: {b_p_value:.4f}\n")

# Interpret the result
# If p-value < 0.05, variances are significantly different (don't assume equal variance)
# If p-value >= 0.05, variances are not significantly different (can assume equal variance)
var_equal = b_p_value >= 0.05
print(f"📊 Equal Variance Assumption: {'✅ Can assume equal variance' if var_equal else '❌ Do NOT assume equal variance'}")
print(f"   (p-value = {b_p_value:.4f})\n")

# 3. Two-Group Comparison: T-Test #################################

## 3.1 Compare Prompt A vs Prompt B #################################

# Extract scores for two prompts to compare
prompt_a_scores = scores.query('prompt_id == "A"')['overall_score']
prompt_b_scores = scores.query('prompt_id == "B"')['overall_score']

print("📊 T-Test: Prompt A vs Prompt B")
print(f"   Mean A: {prompt_a_scores.mean():.2f}")
print(f"   Mean B: {prompt_b_scores.mean():.2f}")
print(f"   Difference: {prompt_a_scores.mean() - prompt_b_scores.mean():.2f}\n")

# Perform t-test using pingouin
# This tests whether the mean scores differ significantly between Prompt A and Prompt B
t_test_result = pg.ttest(prompt_a_scores, prompt_b_scores, correction=not var_equal)

print("📋 T-Test Results:")
print(t_test_result)
print()

# Extract p-value (pingouin 0.6+: p_val; older releases: p-val)
p_value = (
    t_test_result["p_val"].values[0]
    if "p_val" in t_test_result.columns
    else t_test_result["p-val"].values[0]
)

# Interpret the result
print("💡 Interpretation:")
if p_value < 0.05:
    better_prompt = 'A' if prompt_a_scores.mean() > prompt_b_scores.mean() else 'B'
    print(f"   ✅ The difference between Prompt A and Prompt B is statistically significant.")
    print(f"   ✅ Prompt {better_prompt} performs significantly better (p = {p_value:.4f}).")
else:
    print(f"   ❌ The difference between Prompt A and Prompt B is NOT statistically significant.")
    print(f"   ❌ We cannot conclude that one prompt performs better than the other (p = {p_value:.4f}).")
print()

# 4. Three-Group Comparison: ANOVA #################################

## 4.1 One-Way ANOVA #################################

# Perform one-way ANOVA to compare all three prompts simultaneously
# This tests whether at least one prompt differs significantly from the others
# Use pg.anova() if variances are equal, pg.welch_anova() if variances are not equal

if var_equal:
    # Standard ANOVA (equal variances)
    anova_result = pg.anova(dv='overall_score', between='prompt_id', data=scores)
    print("📊 ANOVA: Comparing All Three Prompts (A, B, C) - Equal Variances Assumed")
else:
    # Welch's ANOVA (unequal variances)
    anova_result = pg.welch_anova(dv='overall_score', between='prompt_id', data=scores)
    print("📊 ANOVA: Comparing All Three Prompts (A, B, C) - Unequal Variances (Welch's ANOVA)")

print("\n📋 ANOVA Results:")
print(anova_result)
print()

# Extract F-statistic and p-value (pingouin 0.6+: p_unc; older: p-unc)
f_statistic = anova_result["F"].values[0]
p_value = (
    anova_result["p_unc"].values[0]
    if "p_unc" in anova_result.columns
    else anova_result["p-unc"].values[0]
)

print(f"📊 F-statistic: {f_statistic:.4f}")
print(f"📊 p-value: {p_value:.4f}\n")

## 4.2 Interpret ANOVA Results #################################

print("💡 Interpretation:")
if p_value < 0.05:
    print("   ✅ At least one prompt performs significantly differently from the others.")
    print(f"   ✅ The F-statistic ({f_statistic:.4f}) is significant (p = {p_value:.4f}).")
    print("   ✅ We can conclude that prompt choice significantly affects quality control scores.")
else:
    print("   ❌ We cannot conclude that prompts differ significantly.")
    print(f"   ❌ The F-statistic ({f_statistic:.4f}) is not significant (p = {p_value:.4f}).")
    print("   ❌ Prompt choice does not appear to significantly affect quality control scores.")
print()

# 5. Comparing Specific Quality Dimensions #################################

## 5.1 Formality Comparison #################################

# Compare formality scores across prompts
# Prompt A should score higher on formality (formal writing style)
print("📊 Formality Scores by Prompt:")
formality_stats = scores.groupby('prompt_id')['formality'].agg(['mean', 'std']).round(2)
print(formality_stats)
print()

# ANOVA for formality
formality_anova = pg.welch_anova(dv='formality', between='prompt_id', data=scores)
print("📋 Formality ANOVA Results:")
print(formality_anova)
print()

## 5.2 Succinctness Comparison #################################

# Compare succinctness scores across prompts
# Prompt B should score higher on succinctness (concise writing)
print("📊 Succinctness Scores by Prompt:")
succinctness_stats = scores.groupby('prompt_id')['succinctness'].agg(['mean', 'std']).round(2)
print(succinctness_stats)
print()

# ANOVA for succinctness
succinctness_anova = pg.welch_anova(dv='succinctness', between='prompt_id', data=scores)
print("📋 Succinctness ANOVA Results:")
print(succinctness_anova)
print()

print("✅ Statistical comparison complete!")
print("💡 Key takeaway: Use these statistical tests to determine if prompt differences")
print("   are statistically significant, not just due to random variation.")
