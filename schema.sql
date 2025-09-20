-- users table (employees)
CREATE TABLE users (
                       id BIGSERIAL PRIMARY KEY,
                       email VARCHAR(255) UNIQUE NOT NULL,
                       password VARCHAR(255) NOT NULL,
                       full_name VARCHAR(255) NOT NULL,
                       role VARCHAR(50) DEFAULT 'EMPLOYEE',
                       is_active BOOLEAN DEFAULT TRUE,
                       created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                       updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- customers table
CREATE TABLE customers (
                           id BIGSERIAL PRIMARY KEY,
                           zalo_user_id VARCHAR(255) UNIQUE,
                           phone_number VARCHAR(20) UNIQUE NOT NULL,
                           name VARCHAR(255) NOT NULL,
                           birthdate DATE NOT NULL,
                           created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- vouchers table (voucher templates)
CREATE TABLE vouchers (
                          id BIGSERIAL PRIMARY KEY,
                          code VARCHAR(50) UNIQUE NOT NULL,
                          name VARCHAR(255) NOT NULL,
                          description TEXT,
                          discount_type VARCHAR(20) NOT NULL CHECK (discount_type IN ('AMOUNT', 'PERCENT')),
                          discount_value DECIMAL(10,2) NOT NULL,
                          min_order_value DECIMAL(10,2) DEFAULT 0,
                          max_discount_amount DECIMAL(10,2),
                          valid_from TIMESTAMP NOT NULL,
                          valid_until TIMESTAMP NOT NULL,
                          is_active BOOLEAN DEFAULT TRUE,
                          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                          updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- customer_vouchers table (issued vouchers)
CREATE TABLE customer_vouchers (
                                   id BIGSERIAL PRIMARY KEY,
                                   customer_id BIGINT REFERENCES customers(id),
                                   voucher_id BIGINT REFERENCES vouchers(id),
                                   issued_by_employee_id BIGINT REFERENCES users(id),
                                   voucher_code VARCHAR(100) UNIQUE NOT NULL,
                                   status VARCHAR(20) DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'USED', 'EXPIRED')),
                                   issued_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                   used_at TIMESTAMP NULL,
                                   expires_at TIMESTAMP NOT NULL
);