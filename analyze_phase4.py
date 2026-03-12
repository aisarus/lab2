import pandas as pd

df_before = pd.read_csv("results/phase4_before.csv")
df_after = pd.read_csv("results/phase4_after.csv")

print("--- BEFORE PATCH ---")
for i, row in df_before.iterrows():
    print(f"Bal:{row['bal']:.2f} | N:{row['N']:.2f} | {row['prompt'][:25]}... => {row['N_reason']}")

print("\n--- AFTER PATCH ---")
for i, row in df_after.iterrows():
    print(f"Bal:{row['bal']:.2f} | N:{row['N']:.2f} | {row['prompt'][:25]}... => {row['N_reason']}")

print(f"\nAverage N Before: {df_before['N'].mean():.3f}")
print(f"Average N After:  {df_after['N'].mean():.3f}")
