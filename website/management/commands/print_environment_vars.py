import os

print("Environmental variables:")

for k, v in os.environ.items():
    print(f'\t{k}={v}')