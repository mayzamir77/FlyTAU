USE FLYTAU;
ALTER TABLE Managers
CHANGE COLUMN password manager_password VARCHAR(50) NOT NULL;

ALTER TABLE Registered_Customer
CHANGE COLUMN password customer_password VARCHAR(100) NOT NULL;