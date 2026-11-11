-- =============================================================================
-- PG Connect: MySQL 8.0 Database Schema
-- Character Set: utf8mb4, Collation: utf8mb4_unicode_ci
-- Engine: InnoDB
-- =============================================================================

CREATE DATABASE IF NOT EXISTS `pg_connect_db` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE `pg_connect_db`;

SET FOREIGN_KEY_CHECKS = 0;

-- 1. Users
DROP TABLE IF EXISTS `users`;
CREATE TABLE `users` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `uuid` VARCHAR(36) NOT NULL UNIQUE,
  `email` VARCHAR(255) NOT NULL UNIQUE,
  `password_hash` VARCHAR(255) NOT NULL,
  `full_name` VARCHAR(120) NOT NULL,
  `phone` VARCHAR(20) NOT NULL,
  `role` ENUM('SUPER_ADMIN', 'OWNER', 'MANAGER', 'TENANT') NOT NULL DEFAULT 'TENANT',
  `is_active` BOOLEAN NOT NULL DEFAULT TRUE,
  `is_verified` BOOLEAN NOT NULL DEFAULT FALSE,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX `idx_user_email` (`email`),
  INDEX `idx_user_phone` (`phone`)
) ENGINE=InnoDB;

-- 2. Owner Profiles
DROP TABLE IF EXISTS `owner_profiles`;
CREATE TABLE `owner_profiles` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `user_id` INT NOT NULL UNIQUE,
  `business_name` VARCHAR(150) NOT NULL,
  `pan_number` VARCHAR(20) NULL,
  `aadhaar_last4` CHAR(4) NULL,
  `bank_account_number` VARCHAR(50) NULL,
  `bank_ifsc` VARCHAR(20) NULL,
  `is_approved` BOOLEAN NOT NULL DEFAULT FALSE,
  `approved_by` INT NULL,
  `approved_at` DATETIME NULL,
  FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE,
  FOREIGN KEY (`approved_by`) REFERENCES `users`(`id`) ON DELETE SET NULL
) ENGINE=InnoDB;

-- 3. PG Properties
DROP TABLE IF EXISTS `pg_properties`;
CREATE TABLE `pg_properties` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `uuid` VARCHAR(36) NOT NULL UNIQUE,
  `owner_id` INT NOT NULL,
  `name` VARCHAR(150) NOT NULL,
  `slug` VARCHAR(180) NOT NULL UNIQUE,
  `property_type` ENUM('BOYS', 'GIRLS', 'CO_ED') NOT NULL,
  `address_line1` VARCHAR(255) NOT NULL,
  `address_line2` VARCHAR(255) NULL,
  `locality` VARCHAR(100) NOT NULL,
  `city` VARCHAR(100) NOT NULL,
  `state` VARCHAR(100) NOT NULL,
  `pincode` VARCHAR(10) NOT NULL,
  `latitude` DECIMAL(10, 8) NOT NULL,
  `longitude` DECIMAL(11, 8) NOT NULL,
  `contact_phone` VARCHAR(20) NOT NULL,
  `contact_email` VARCHAR(120) NOT NULL,
  `description` TEXT NOT NULL,
  `rules` TEXT NULL,
  `notice_period_days` INT NOT NULL DEFAULT 30,
  `gate_closing_time` VARCHAR(20) DEFAULT '22:30',
  `is_verified` BOOLEAN NOT NULL DEFAULT FALSE,
  `is_active` BOOLEAN NOT NULL DEFAULT TRUE,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX `idx_prop_city` (`city`),
  INDEX `idx_prop_locality` (`locality`),
  INDEX `idx_prop_pincode` (`pincode`),
  FOREIGN KEY (`owner_id`) REFERENCES `owner_profiles`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB;

-- 4. Manager Assignments
DROP TABLE IF EXISTS `manager_assignments`;
CREATE TABLE `manager_assignments` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `manager_user_id` INT NOT NULL,
  `property_id` INT NOT NULL,
  `assigned_by` INT NULL,
  `can_manage_payments` BOOLEAN NOT NULL DEFAULT TRUE,
  `can_manage_complaints` BOOLEAN NOT NULL DEFAULT TRUE,
  `is_active` BOOLEAN NOT NULL DEFAULT TRUE,
  `assigned_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY `uq_manager_property` (`manager_user_id`, `property_id`),
  FOREIGN KEY (`manager_user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE,
  FOREIGN KEY (`property_id`) REFERENCES `pg_properties`(`id`) ON DELETE CASCADE,
  FOREIGN KEY (`assigned_by`) REFERENCES `users`(`id`) ON DELETE SET NULL
) ENGINE=InnoDB;

-- 5. Staff
DROP TABLE IF EXISTS `staff`;
CREATE TABLE `staff` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `property_id` INT NOT NULL,
  `full_name` VARCHAR(120) NOT NULL,
  `role_designation` VARCHAR(60) NOT NULL,
  `phone` VARCHAR(20) NOT NULL,
  `salary_amount` DECIMAL(10,2) NOT NULL DEFAULT 0.00,
  `is_active` BOOLEAN NOT NULL DEFAULT TRUE,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (`property_id`) REFERENCES `pg_properties`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB;

-- 6. Property Photos
DROP TABLE IF EXISTS `property_photos`;
CREATE TABLE `property_photos` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `property_id` INT NOT NULL,
  `file_path` VARCHAR(255) NOT NULL,
  `caption` VARCHAR(100) NULL,
  `is_primary` BOOLEAN NOT NULL DEFAULT FALSE,
  `uploaded_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (`property_id`) REFERENCES `pg_properties`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB;

-- 7. Property Facilities
DROP TABLE IF EXISTS `property_facilities`;
CREATE TABLE `property_facilities` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `property_id` INT NOT NULL UNIQUE,
  `has_wifi` BOOLEAN NOT NULL DEFAULT TRUE,
  `has_ac` BOOLEAN NOT NULL DEFAULT FALSE,
  `has_washing_machine` BOOLEAN NOT NULL DEFAULT TRUE,
  `has_parking` BOOLEAN NOT NULL DEFAULT TRUE,
  `has_housekeeping` BOOLEAN NOT NULL DEFAULT TRUE,
  `has_cctv` BOOLEAN NOT NULL DEFAULT TRUE,
  `has_drinking_water` BOOLEAN NOT NULL DEFAULT TRUE,
  `has_power_backup` BOOLEAN NOT NULL DEFAULT TRUE,
  `has_attached_washroom` BOOLEAN NOT NULL DEFAULT FALSE,
  `has_refrigerator` BOOLEAN NOT NULL DEFAULT FALSE,
  `has_biometric_access` BOOLEAN NOT NULL DEFAULT FALSE,
  FOREIGN KEY (`property_id`) REFERENCES `pg_properties`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB;

-- 8. Rooms
DROP TABLE IF EXISTS `rooms`;
CREATE TABLE `rooms` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `property_id` INT NOT NULL,
  `room_number` VARCHAR(20) NOT NULL,
  `floor_number` INT NOT NULL DEFAULT 1,
  `sharing_type` ENUM('SINGLE', 'DOUBLE', 'TRIPLE', 'FOUR') NOT NULL,
  `has_ac` BOOLEAN NOT NULL DEFAULT FALSE,
  `has_attached_bathroom` BOOLEAN NOT NULL DEFAULT FALSE,
  `monthly_rent_per_bed` DECIMAL(10,2) NOT NULL,
  `security_deposit_per_bed` DECIMAL(10,2) NOT NULL,
  `is_active` BOOLEAN NOT NULL DEFAULT TRUE,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY `uq_property_room` (`property_id`, `room_number`),
  FOREIGN KEY (`property_id`) REFERENCES `pg_properties`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB;

-- 9. Beds
DROP TABLE IF EXISTS `beds`;
CREATE TABLE `beds` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `room_id` INT NOT NULL,
  `bed_label` VARCHAR(10) NOT NULL,
  `status` ENUM('AVAILABLE', 'RESERVED', 'OCCUPIED', 'MAINTENANCE', 'INACTIVE') NOT NULL DEFAULT 'AVAILABLE',
  `last_status_change` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `notes` VARCHAR(255) NULL,
  INDEX `idx_bed_status` (`status`),
  UNIQUE KEY `uq_room_bed` (`room_id`, `bed_label`),
  FOREIGN KEY (`room_id`) REFERENCES `rooms`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB;

-- 10. Tenants
DROP TABLE IF EXISTS `tenants`;
CREATE TABLE `tenants` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `user_id` INT NOT NULL UNIQUE,
  `emergency_contact_name` VARCHAR(120) NOT NULL,
  `emergency_contact_phone` VARCHAR(20) NOT NULL,
  `emergency_contact_relation` VARCHAR(50) NOT NULL,
  `id_proof_type` VARCHAR(50) NOT NULL,
  `id_proof_number_masked` VARCHAR(50) NOT NULL,
  `college_or_company_name` VARCHAR(150) NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB;

-- 11. Room Allocations
DROP TABLE IF EXISTS `room_allocations`;
CREATE TABLE `room_allocations` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `tenant_id` INT NOT NULL,
  `bed_id` INT NOT NULL,
  `check_in_date` DATE NOT NULL,
  `check_out_date` DATE NULL,
  `monthly_rent_agreed` DECIMAL(10,2) NOT NULL,
  `security_deposit_paid` DECIMAL(10,2) NOT NULL,
  `is_active` BOOLEAN NOT NULL DEFAULT TRUE,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (`tenant_id`) REFERENCES `tenants`(`id`) ON DELETE CASCADE,
  FOREIGN KEY (`bed_id`) REFERENCES `beds`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB;

-- 12. Bookings
DROP TABLE IF EXISTS `bookings`;
CREATE TABLE `bookings` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `booking_reference` VARCHAR(30) NOT NULL UNIQUE,
  `customer_id` INT NOT NULL,
  `property_id` INT NOT NULL,
  `room_id` INT NULL,
  `bed_id` INT NULL,
  `preferred_move_in_date` DATE NOT NULL,
  `sharing_type` VARCHAR(20) NOT NULL,
  `status` ENUM('PENDING', 'APPROVED', 'REJECTED', 'CANCELLED', 'EXPIRED', 'COMPLETED') NOT NULL DEFAULT 'PENDING',
  `admin_remarks` TEXT NULL,
  `reservation_expires_at` DATETIME NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX `idx_booking_ref` (`booking_reference`),
  INDEX `idx_booking_status` (`status`),
  FOREIGN KEY (`customer_id`) REFERENCES `users`(`id`) ON DELETE CASCADE,
  FOREIGN KEY (`property_id`) REFERENCES `pg_properties`(`id`) ON DELETE CASCADE,
  FOREIGN KEY (`room_id`) REFERENCES `rooms`(`id`) ON DELETE SET NULL,
  FOREIGN KEY (`bed_id`) REFERENCES `beds`(`id`) ON DELETE SET NULL
) ENGINE=InnoDB;

-- 13. Booking History
DROP TABLE IF EXISTS `booking_history`;
CREATE TABLE `booking_history` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `booking_id` INT NOT NULL,
  `from_status` VARCHAR(30) NULL,
  `to_status` VARCHAR(30) NOT NULL,
  `changed_by_user_id` INT NULL,
  `change_reason` TEXT NULL,
  `recorded_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (`booking_id`) REFERENCES `bookings`(`id`) ON DELETE CASCADE,
  FOREIGN KEY (`changed_by_user_id`) REFERENCES `users`(`id`) ON DELETE SET NULL
) ENGINE=InnoDB;

-- 14. Rent Invoices
DROP TABLE IF EXISTS `rent_invoices`;
CREATE TABLE `rent_invoices` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `invoice_number` VARCHAR(50) NOT NULL UNIQUE,
  `property_id` INT NOT NULL,
  `tenant_id` INT NOT NULL,
  `allocation_id` INT NOT NULL,
  `billing_month` INT NOT NULL,
  `billing_year` INT NOT NULL,
  `base_rent_amount` DECIMAL(10,2) NOT NULL,
  `electricity_charges` DECIMAL(10,2) NOT NULL DEFAULT 0.00,
  `food_charges` DECIMAL(10,2) NOT NULL DEFAULT 0.00,
  `late_fee_amount` DECIMAL(10,2) NOT NULL DEFAULT 0.00,
  `total_amount_due` DECIMAL(10,2) NOT NULL,
  `amount_paid` DECIMAL(10,2) NOT NULL DEFAULT 0.00,
  `due_date` DATE NOT NULL,
  `status` ENUM('PENDING', 'PARTIALLY_PAID', 'PAID', 'OVERDUE') NOT NULL DEFAULT 'PENDING',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX `idx_inv_status` (`status`),
  FOREIGN KEY (`property_id`) REFERENCES `pg_properties`(`id`) ON DELETE CASCADE,
  FOREIGN KEY (`tenant_id`) REFERENCES `tenants`(`id`) ON DELETE CASCADE,
  FOREIGN KEY (`allocation_id`) REFERENCES `room_allocations`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB;

-- 15. Payments
DROP TABLE IF EXISTS `payments`;
CREATE TABLE `payments` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `payment_reference` VARCHAR(50) NOT NULL UNIQUE,
  `invoice_id` INT NOT NULL,
  `tenant_id` INT NOT NULL,
  `amount` DECIMAL(10,2) NOT NULL,
  `payment_method` ENUM('CASH', 'UPI', 'BANK_TRANSFER', 'CHEQUE') NOT NULL,
  `transaction_reference` VARCHAR(100) NULL,
  `payment_date` DATE NOT NULL,
  `status` ENUM('COMPLETED', 'PENDING_VERIFICATION', 'REFUNDED') NOT NULL DEFAULT 'COMPLETED',
  `verified_by_user_id` INT NULL,
  `notes` TEXT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (`invoice_id`) REFERENCES `rent_invoices`(`id`) ON DELETE CASCADE,
  FOREIGN KEY (`tenant_id`) REFERENCES `tenants`(`id`) ON DELETE CASCADE,
  FOREIGN KEY (`verified_by_user_id`) REFERENCES `users`(`id`) ON DELETE SET NULL
) ENGINE=InnoDB;

-- 16. Security Deposits
DROP TABLE IF EXISTS `security_deposits`;
CREATE TABLE `security_deposits` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `tenant_id` INT NOT NULL,
  `property_id` INT NOT NULL,
  `amount_deposited` DECIMAL(10,2) NOT NULL,
  `deposit_date` DATE NOT NULL,
  `deductions_amount` DECIMAL(10,2) NOT NULL DEFAULT 0.00,
  `deduction_reason` TEXT NULL,
  `refund_amount` DECIMAL(10,2) NOT NULL DEFAULT 0.00,
  `refund_date` DATE NULL,
  `refund_status` ENUM('HELD', 'PARTIALLY_REFUNDED', 'FULLY_REFUNDED') NOT NULL DEFAULT 'HELD',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (`tenant_id`) REFERENCES `tenants`(`id`) ON DELETE CASCADE,
  FOREIGN KEY (`property_id`) REFERENCES `pg_properties`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB;

-- 17. Expenses
DROP TABLE IF EXISTS `expenses`;
CREATE TABLE `expenses` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `property_id` INT NOT NULL,
  `category` ENUM('ELECTRICITY', 'WATER', 'MAINTENANCE', 'INTERNET', 'GROCERY_FOOD', 'SALARY', 'TAX', 'MISCELLANEOUS') NOT NULL,
  `amount` DECIMAL(10,2) NOT NULL,
  `expense_date` DATE NOT NULL,
  `description` VARCHAR(255) NOT NULL,
  `receipt_file_path` VARCHAR(255) NULL,
  `recorded_by_user_id` INT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (`property_id`) REFERENCES `pg_properties`(`id`) ON DELETE CASCADE,
  FOREIGN KEY (`recorded_by_user_id`) REFERENCES `users`(`id`) ON DELETE SET NULL
) ENGINE=InnoDB;

-- 18. Food Menus
DROP TABLE IF EXISTS `food_menus`;
CREATE TABLE `food_menus` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `property_id` INT NOT NULL,
  `day_of_week` ENUM('MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY', 'SATURDAY', 'SUNDAY') NOT NULL,
  `meal_type` ENUM('BREAKFAST', 'LUNCH', 'DINNER', 'EVENING_SNACKS') NOT NULL,
  `items_menu` TEXT NOT NULL,
  `is_veg` BOOLEAN NOT NULL DEFAULT TRUE,
  `special_dietary_notes` VARCHAR(255) NULL,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY `uq_property_day_meal` (`property_id`, `day_of_week`, `meal_type`),
  FOREIGN KEY (`property_id`) REFERENCES `pg_properties`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB;

-- 19. Complaints
DROP TABLE IF EXISTS `complaints`;
CREATE TABLE `complaints` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `ticket_number` VARCHAR(30) NOT NULL UNIQUE,
  `property_id` INT NOT NULL,
  `tenant_id` INT NOT NULL,
  `room_id` INT NULL,
  `category` ENUM('PLUMBING', 'ELECTRICAL', 'WIFI_NETWORK', 'CLEANING', 'FOOD_QUALITY', 'NOISE_DISTURBANCE', 'OTHER') NOT NULL,
  `title` VARCHAR(150) NOT NULL,
  `description` TEXT NOT NULL,
  `photo_file_path` VARCHAR(255) NULL,
  `priority` ENUM('LOW', 'MEDIUM', 'HIGH', 'URGENT') NOT NULL DEFAULT 'MEDIUM',
  `status` ENUM('OPEN', 'ASSIGNED', 'IN_PROGRESS', 'RESOLVED', 'CLOSED') NOT NULL DEFAULT 'OPEN',
  `assigned_staff_id` INT NULL,
  `resolved_at` DATETIME NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX `idx_complaint_status` (`status`),
  FOREIGN KEY (`property_id`) REFERENCES `pg_properties`(`id`) ON DELETE CASCADE,
  FOREIGN KEY (`tenant_id`) REFERENCES `tenants`(`id`) ON DELETE CASCADE,
  FOREIGN KEY (`room_id`) REFERENCES `rooms`(`id`) ON DELETE SET NULL,
  FOREIGN KEY (`assigned_staff_id`) REFERENCES `staff`(`id`) ON DELETE SET NULL
) ENGINE=InnoDB;

-- 20. Complaint Updates
DROP TABLE IF EXISTS `complaint_updates`;
CREATE TABLE `complaint_updates` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `complaint_id` INT NOT NULL,
  `updated_by_user_id` INT NULL,
  `status` VARCHAR(30) NOT NULL,
  `note` TEXT NOT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (`complaint_id`) REFERENCES `complaints`(`id`) ON DELETE CASCADE,
  FOREIGN KEY (`updated_by_user_id`) REFERENCES `users`(`id`) ON DELETE SET NULL
) ENGINE=InnoDB;

-- 21. Reviews
DROP TABLE IF EXISTS `reviews`;
CREATE TABLE `reviews` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `property_id` INT NOT NULL,
  `user_id` INT NOT NULL,
  `allocation_id` INT NOT NULL UNIQUE,
  `rating` TINYINT NOT NULL CHECK (`rating` BETWEEN 1 AND 5),
  `cleanliness_rating` TINYINT NOT NULL CHECK (`cleanliness_rating` BETWEEN 1 AND 5),
  `food_rating` TINYINT NOT NULL CHECK (`food_rating` BETWEEN 1 AND 5),
  `comment` TEXT NOT NULL,
  `is_approved` BOOLEAN NOT NULL DEFAULT TRUE,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (`property_id`) REFERENCES `pg_properties`(`id`) ON DELETE CASCADE,
  FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE,
  FOREIGN KEY (`allocation_id`) REFERENCES `room_allocations`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB;

-- 22. Wishlists
DROP TABLE IF EXISTS `wishlists`;
CREATE TABLE `wishlists` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `user_id` INT NOT NULL,
  `property_id` INT NOT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY `uq_user_property_wishlist` (`user_id`, `property_id`),
  FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE,
  FOREIGN KEY (`property_id`) REFERENCES `pg_properties`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB;

-- 23. Notifications
DROP TABLE IF EXISTS `notifications`;
CREATE TABLE `notifications` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `user_id` INT NOT NULL,
  `title` VARCHAR(120) NOT NULL,
  `message` TEXT NOT NULL,
  `notification_type` VARCHAR(50) NOT NULL,
  `related_entity_type` VARCHAR(50) NULL,
  `related_entity_id` INT NULL,
  `is_read` BOOLEAN NOT NULL DEFAULT FALSE,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX `idx_notif_user` (`user_id`, `is_read`),
  FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB;

-- 24. Visitor Logs
DROP TABLE IF EXISTS `visitor_logs`;
CREATE TABLE `visitor_logs` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `property_id` INT NOT NULL,
  `tenant_id` INT NOT NULL,
  `visitor_name` VARCHAR(120) NOT NULL,
  `visitor_phone` VARCHAR(20) NOT NULL,
  `visit_date` DATE NOT NULL,
  `check_in_time` TIME NOT NULL,
  `check_out_time` TIME NULL,
  `relationship` VARCHAR(50) NOT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (`property_id`) REFERENCES `pg_properties`(`id`) ON DELETE CASCADE,
  FOREIGN KEY (`tenant_id`) REFERENCES `tenants`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB;

-- 25. Property Verifications
DROP TABLE IF EXISTS `property_verifications`;
CREATE TABLE `property_verifications` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `property_id` INT NOT NULL,
  `reviewed_by_admin_id` INT NULL,
  `status` ENUM('SUBMITTED', 'IN_REVIEW', 'APPROVED', 'REJECTED') NOT NULL DEFAULT 'SUBMITTED',
  `rejection_reason` TEXT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (`property_id`) REFERENCES `pg_properties`(`id`) ON DELETE CASCADE,
  FOREIGN KEY (`reviewed_by_admin_id`) REFERENCES `users`(`id`) ON DELETE SET NULL
) ENGINE=InnoDB;

-- 26. Audit Logs
DROP TABLE IF EXISTS `audit_logs`;
CREATE TABLE `audit_logs` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `user_id` INT NULL,
  `action` VARCHAR(100) NOT NULL,
  `entity_name` VARCHAR(50) NOT NULL,
  `entity_id` INT NULL,
  `ip_address` VARCHAR(45) NULL,
  `details_json` JSON NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX `idx_audit_action` (`action`),
  FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE SET NULL
) ENGINE=InnoDB;

SET FOREIGN_KEY_CHECKS = 1;
