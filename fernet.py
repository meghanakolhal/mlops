from cryptography.fernet import Fernet

# Generate a Fernet key
key = Fernet.generate_key()

# Print the key to use it in your configuration
print(key.decode())
