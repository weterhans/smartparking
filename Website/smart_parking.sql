-- phpMyAdmin SQL Dump
-- version 5.2.2
-- https://www.phpmyadmin.net/
--
-- Host: localhost:3306
-- Generation Time: Jun 22, 2026 at 04:07 PM
-- Server version: 12.2.2-MariaDB
-- PHP Version: 8.3.16

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `smart_parking`
--

-- --------------------------------------------------------

--
-- Table structure for table `parking_history`
--

CREATE TABLE `parking_history` (
  `date` date NOT NULL,
  `vehicle_count` int(11) DEFAULT 0
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_uca1400_ai_ci;

--
-- Dumping data for table `parking_history`
--

INSERT INTO `parking_history` (`date`, `vehicle_count`) VALUES
('2026-06-19', 4),
('2026-06-20', 5),
('2026-06-21', 5),
('2026-06-22', 1);

-- --------------------------------------------------------

--
-- Table structure for table `parking_slots`
--

CREATE TABLE `parking_slots` (
  `id` varchar(50) NOT NULL,
  `status` enum('Tersedia','Terisi','Maintenance') DEFAULT 'Tersedia',
  `check_in` datetime DEFAULT NULL,
  `updated_at` timestamp NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  `vehicle_type` varchar(20) DEFAULT 'Kecil'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_uca1400_ai_ci;

--
-- Dumping data for table `parking_slots`
--

INSERT INTO `parking_slots` (`id`, `status`, `check_in`, `updated_at`, `vehicle_type`) VALUES
('Slot_A1', 'Terisi', '2026-06-22 22:45:22', '2026-06-22 08:45:22', 'Kecil'),
('Slot_A2', 'Terisi', '2026-06-22 23:06:39', '2026-06-22 09:06:39', 'Kecil'),
('Slot_A3', 'Terisi', '2026-06-22 22:44:14', '2026-06-22 08:44:14', 'Besar'),
('Slot_A4', 'Terisi', '2026-06-22 22:48:59', '2026-06-22 08:48:59', 'Kecil'),
('Slot_A5', 'Terisi', '2026-06-22 22:51:53', '2026-06-22 08:51:53', 'Besar'),
('Slot_A6', 'Tersedia', NULL, '2026-04-21 09:08:00', 'Kecil');

-- --------------------------------------------------------

--
-- Table structure for table `subscriptions`
--

CREATE TABLE `subscriptions` (
  `id` varchar(50) NOT NULL,
  `name` varchar(255) NOT NULL,
  `card_uid` varchar(100) DEFAULT NULL,
  `status` enum('active','inactive') DEFAULT 'active',
  `created_at` timestamp NULL DEFAULT current_timestamp(),
  `slot_id` varchar(50) DEFAULT NULL,
  `expired_at` date DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_uca1400_ai_ci;

--
-- Dumping data for table `subscriptions`
--

INSERT INTO `subscriptions` (`id`, `name`, `card_uid`, `status`, `created_at`, `slot_id`, `expired_at`) VALUES
('USER001', '', '832B3434', 'inactive', '2026-06-22 08:26:16', NULL, NULL),
('USER002', '', '3A5D0307', 'inactive', '2026-06-22 08:26:16', NULL, NULL),
('USER003', '', 'C10E0407', 'inactive', '2026-06-22 08:26:16', NULL, NULL);

-- --------------------------------------------------------

--
-- Table structure for table `transactions`
--

CREATE TABLE `transactions` (
  `id` varchar(100) NOT NULL,
  `slot_id` varchar(50) DEFAULT NULL,
  `user_identifier` varchar(100) DEFAULT NULL,
  `transaction_date` date DEFAULT NULL,
  `transaction_timestamp` bigint(20) DEFAULT NULL,
  `duration_hours` int(11) DEFAULT NULL,
  `fee` decimal(10,2) DEFAULT NULL,
  `is_subscriber` tinyint(1) DEFAULT NULL,
  `vehicle_type` varchar(50) DEFAULT 'Kecil'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_uca1400_ai_ci;

--
-- Dumping data for table `transactions`
--

INSERT INTO `transactions` (`id`, `slot_id`, `user_identifier`, `transaction_date`, `transaction_timestamp`, `duration_hours`, `fee`, `is_subscriber`, `vehicle_type`) VALUES
('CB36C5', 'Slot_A5', 'Guest', '2026-06-22', 1782140160, 1, 5000.00, 0, 'Kecil'),
('EFB72B', 'Slot_A4', 'Guest', '2026-06-21', 1782038756, 1, 5000.00, 0, 'Kecil'),
('F3677A', 'Slot_A5', 'Guest', '2026-06-22', 1782143446, 1, 5000.00, 0, 'Kecil');

-- --------------------------------------------------------

--
-- Table structure for table `users`
--

CREATE TABLE `users` (
  `uid` varchar(128) NOT NULL,
  `email` varchar(255) NOT NULL,
  `username` varchar(100) NOT NULL,
  `nama` varchar(255) NOT NULL,
  `no_hp` varchar(20) DEFAULT NULL,
  `role` varchar(50) DEFAULT 'user',
  `created_at` timestamp NULL DEFAULT current_timestamp(),
  `password_hash` varchar(255) NOT NULL DEFAULT '',
  `jenis_kelamin` varchar(20) DEFAULT '',
  `tanggal_lahir` date DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_uca1400_ai_ci;

--
-- Dumping data for table `users`
--

INSERT INTO `users` (`uid`, `email`, `username`, `nama`, `no_hp`, `role`, `created_at`, `password_hash`, `jenis_kelamin`, `tanggal_lahir`) VALUES
('5bb9ace6462848d3a644dc8485cdcbd3', 'admin@smartparking.com', 'admin', 'Administrator', '', 'admin', '2026-04-09 09:20:34', '$2b$12$TnG/xD0uB7aHBSx16/9b2eiKrg6MMtCLSbDebuDv0/ogs8C6I5Ri.', '', NULL);

--
-- Indexes for dumped tables
--

--
-- Indexes for table `parking_history`
--
ALTER TABLE `parking_history`
  ADD PRIMARY KEY (`date`);

--
-- Indexes for table `parking_slots`
--
ALTER TABLE `parking_slots`
  ADD PRIMARY KEY (`id`);

--
-- Indexes for table `subscriptions`
--
ALTER TABLE `subscriptions`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `card_uid` (`card_uid`),
  ADD KEY `fk_sub_slot` (`slot_id`);

--
-- Indexes for table `transactions`
--
ALTER TABLE `transactions`
  ADD PRIMARY KEY (`id`),
  ADD KEY `idx_transactions_date` (`transaction_date`),
  ADD KEY `idx_transactions_slot` (`slot_id`),
  ADD KEY `idx_transactions_user` (`user_identifier`);

--
-- Indexes for table `users`
--
ALTER TABLE `users`
  ADD PRIMARY KEY (`uid`),
  ADD UNIQUE KEY `email` (`email`);

--
-- Constraints for dumped tables
--

--
-- Constraints for table `subscriptions`
--
ALTER TABLE `subscriptions`
  ADD CONSTRAINT `fk_sub_slot` FOREIGN KEY (`slot_id`) REFERENCES `parking_slots` (`id`);

--
-- Constraints for table `transactions`
--
ALTER TABLE `transactions`
  ADD CONSTRAINT `1` FOREIGN KEY (`slot_id`) REFERENCES `parking_slots` (`id`) ON DELETE SET NULL;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
