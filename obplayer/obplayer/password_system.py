import passlib.hash as hashing

# Builds password hash/salt, and returns the data for storage.
def create_password_hash(password):
    return hashing.bcrypt.hash(password)
# Checks if the user provided when hashed
# matches the hash in the db.
def login_check(input_password, db_hash):
    return hashing.bcrypt.verify(input_password, db_hash)