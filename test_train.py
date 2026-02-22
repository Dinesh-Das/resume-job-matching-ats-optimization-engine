import time
from server import train_model

if __name__ == "__main__":
    print("Starting training pipeline...")
    start = time.time()
    result = train_model()
    end = time.time()
    print(f"Training pipeline finished in {end - start:.2f} seconds.")
    print("Result:", result)
