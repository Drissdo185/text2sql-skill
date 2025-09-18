# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Spring Boot 3.5.6 application using Java 21 called "Radi_battery". It's a basic Spring Boot web application with security features enabled.

## Build and Development Commands

### Building the Application
```bash
./mvnw clean compile
```

### Running the Application
```bash
./mvnw spring-boot:run
```

### Running Tests
```bash
./mvnw test
```

### Packaging the Application
```bash
./mvnw clean package
```

### Full Build with Tests
```bash
./mvnw clean install
```

## Architecture

- **Framework**: Spring Boot 3.5.6 with Spring Security and Spring Web
- **Java Version**: 21
- **Build Tool**: Maven with wrapper (mvnw)
- **Main Package**: `com.example.radi_battery`
- **Application Entry Point**: `RadiBatteryApplication.java`

### Key Dependencies
- Spring Boot Starter Web (REST APIs and web functionality)
- Spring Boot Starter Security (authentication and authorization)
- Lombok (code generation for boilerplate)
- Spring Boot Test (testing framework)
- Spring Security Test (security testing utilities)

### Project Structure
```
src/
├── main/
│   ├── java/com/example/radi_battery/
│   │   └── RadiBatteryApplication.java
│   └── resources/
│       ├── application.properties
│       ├── static/
│       └── templates/
└── test/
    └── java/com/example/radi_battery/
        └── RadiBatteryApplicationTests.java
```

### Configuration
- Main configuration file: `src/main/resources/application.properties`
- Database: PostgreSQL with JPA/Hibernate
- Security: Custom security configuration with CORS support
- Zalo Integration: OA and ZNS API configuration for notifications

## API Endpoints

### Customer Management
- `GET /api/customers/{id}` - Get customer by ID
- `GET /api/customers/zalo/{zaloUserId}` - Get customer by Zalo User ID
- `GET /api/customers/phone/{phoneNumber}` - Get customer by phone number
- `POST /api/customers/search` - Search customers by keyword
- `POST /api/customers` - Create new customer
- `PUT /api/customers/{id}` - Update customer
- `PUT /api/customers/{id}/purchase` - Update purchase statistics

### Voucher Management
- `POST /api/vouchers/create` - Create and send voucher to customer
- `GET /api/vouchers/code/{voucherCode}` - Get voucher by code
- `GET /api/vouchers/customer/{customerId}` - Get all vouchers for customer
- `GET /api/vouchers/customer/{customerId}/active` - Get active vouchers for customer
- `POST /api/vouchers/use/{voucherCode}` - Use a voucher
- `GET /api/vouchers/validate/{voucherCode}` - Validate voucher for purchase amount
- `GET /api/vouchers/discount/{voucherCode}` - Calculate discount amount

## Database Setup
Before running the application, ensure PostgreSQL is running and create the database:
```sql
CREATE DATABASE radi_battery;
CREATE USER radi_user WITH PASSWORD 'radi_password';
GRANT ALL PRIVILEGES ON DATABASE radi_battery TO radi_user;
```

## Environment Variables
Set the following in `application.properties`:
- `zalo.oa.access_token` - Zalo OA Access Token
- `zalo.zns.app_id` - Zalo ZNS App ID
- `zalo.zns.template_id` - ZNS Template ID for voucher notifications