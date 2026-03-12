import pandas as pd
df = pd.read_csv("results/phase5_temp.csv")

# We want the variance of the judge ON THE EXACT SAME TEXT over 5 repeats.
# So we group by 'prompt' and 'temp', calculate std, and then average those stds across the prompts.
std_per_prompt = df.groupby(['prompt', 'temp'])[['E', 'F', 'N', 'M', 'B', 'bal']].std()
mean_std_by_temp = std_per_prompt.groupby('temp').mean().round(4)

print("\n[PHASE 5] Average Standard Deviation (Sigma) PER PROMPT by Temperature:")
print("How much the Judge's scores fluctuate on the exact same text:")
print(mean_std_by_temp)
