CREATE DATABASE  IF NOT EXISTS `flytau` /*!40100 DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci */ /*!80016 DEFAULT ENCRYPTION='N' */;
USE `flytau`;
-- MySQL dump 10.13  Distrib 8.0.30, for Win64 (x86_64)
--
-- Host: 127.0.0.1    Database: flytau
-- ------------------------------------------------------
-- Server version	8.0.30

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `aircraft`
--

DROP TABLE IF EXISTS `aircraft`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `aircraft` (
  `aircraft_id` varchar(50) NOT NULL,
  `manufacturer` varchar(20) NOT NULL,
  `size` varchar(30) NOT NULL,
  `purchase_date` date DEFAULT NULL,
  PRIMARY KEY (`aircraft_id`),
  CONSTRAINT `aircraft_chk_1` CHECK ((`manufacturer` in (_utf8mb4'Boeing',_utf8mb4'Airbus',_utf8mb4'Dassault'))),
  CONSTRAINT `aircraft_chk_2` CHECK ((`size` in (_utf8mb4'Large',_utf8mb4'Small')))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `booking`
--

DROP TABLE IF EXISTS `booking`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `booking` (
  `booking_id` varchar(50) NOT NULL,
  `customer_email` varchar(100) NOT NULL,
  `flight_id` varchar(20) NOT NULL,
  `booking_date` date DEFAULT NULL,
  `booking_status` varchar(50) NOT NULL,
  PRIMARY KEY (`booking_id`),
  KEY `customer_email` (`customer_email`),
  KEY `flight_id` (`flight_id`),
  CONSTRAINT `booking_ibfk_1` FOREIGN KEY (`customer_email`) REFERENCES `customer` (`email`),
  CONSTRAINT `booking_ibfk_2` FOREIGN KEY (`flight_id`) REFERENCES `flight` (`flight_id`),
  CONSTRAINT `booking_chk_1` CHECK ((`booking_status` in (_utf8mb4'Active',_utf8mb4'Completed',_utf8mb4'Customer Cancellation',_utf8mb4'System Cancellation')))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `class`
--

DROP TABLE IF EXISTS `class`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `class` (
  `aircraft_id` varchar(50) NOT NULL,
  `class_type` varchar(20) NOT NULL,
  `num_rows` int DEFAULT NULL,
  `num_columns` int DEFAULT NULL,
  PRIMARY KEY (`aircraft_id`,`class_type`),
  CONSTRAINT `class_ibfk_1` FOREIGN KEY (`aircraft_id`) REFERENCES `aircraft` (`aircraft_id`),
  CONSTRAINT `class_chk_1` CHECK ((`class_type` in (_utf8mb4'economy',_utf8mb4'business')))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `classes_in_flight`
--

DROP TABLE IF EXISTS `classes_in_flight`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `classes_in_flight` (
  `flight_id` varchar(20) NOT NULL,
  `aircraft_id` varchar(50) NOT NULL,
  `class_type` varchar(20) NOT NULL,
  `seat_price` decimal(10,2) NOT NULL,
  PRIMARY KEY (`flight_id`,`aircraft_id`,`class_type`),
  KEY `aircraft_id` (`aircraft_id`,`class_type`),
  CONSTRAINT `classes_in_flight_ibfk_1` FOREIGN KEY (`flight_id`) REFERENCES `flight` (`flight_id`),
  CONSTRAINT `classes_in_flight_ibfk_2` FOREIGN KEY (`aircraft_id`, `class_type`) REFERENCES `class` (`aircraft_id`, `class_type`),
  CONSTRAINT `classes_in_flight_chk_1` CHECK ((`class_type` in (_utf8mb4'economy',_utf8mb4'business')))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `customer`
--

DROP TABLE IF EXISTS `customer`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `customer` (
  `email` varchar(100) NOT NULL,
  `first_name_english` varchar(50) NOT NULL,
  `last_name_english` varchar(50) NOT NULL,
  PRIMARY KEY (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `customer_phone_numbers`
--

DROP TABLE IF EXISTS `customer_phone_numbers`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `customer_phone_numbers` (
  `email` varchar(100) NOT NULL,
  `phone_number` varchar(15) NOT NULL,
  PRIMARY KEY (`email`,`phone_number`),
  CONSTRAINT `customer_phone_numbers_ibfk_1` FOREIGN KEY (`email`) REFERENCES `customer` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `flight`
--

DROP TABLE IF EXISTS `flight`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `flight` (
  `flight_id` varchar(20) NOT NULL,
  `flight_duration` int NOT NULL,
  `flight_status` varchar(20) NOT NULL,
  `departure_time` time NOT NULL,
  `departure_date` date NOT NULL,
  `origin_airport` varchar(10) NOT NULL,
  `destination_airport` varchar(10) NOT NULL,
  `aircraft_id` varchar(50) NOT NULL,
  PRIMARY KEY (`flight_id`),
  KEY `aircraft_id` (`aircraft_id`),
  CONSTRAINT `flight_ibfk_1` FOREIGN KEY (`aircraft_id`) REFERENCES `aircraft` (`aircraft_id`),
  CONSTRAINT `flight_chk_1` CHECK ((`flight_status` in (_utf8mb4'Active',_utf8mb4'Fully Booked',_utf8mb4'Completed',_utf8mb4'Cancelled')))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `flight_attendants`
--

DROP TABLE IF EXISTS `flight_attendants`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `flight_attendants` (
  `attendant_id` varchar(50) NOT NULL,
  `first_name_hebrew` varchar(50) NOT NULL,
  `last_name_hebrew` varchar(50) NOT NULL,
  `phone` varchar(15) DEFAULT NULL,
  `city` varchar(50) DEFAULT NULL,
  `street` varchar(50) DEFAULT NULL,
  `house_number` int DEFAULT NULL,
  `start_date` date NOT NULL,
  `long_flight_certified` tinyint(1) NOT NULL,
  PRIMARY KEY (`attendant_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `flight_attendants_assignment`
--

DROP TABLE IF EXISTS `flight_attendants_assignment`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `flight_attendants_assignment` (
  `flight_id` varchar(20) NOT NULL,
  `attendant_id` varchar(50) NOT NULL,
  PRIMARY KEY (`flight_id`,`attendant_id`),
  KEY `attendant_id` (`attendant_id`),
  CONSTRAINT `flight_attendants_assignment_ibfk_1` FOREIGN KEY (`flight_id`) REFERENCES `flight` (`flight_id`),
  CONSTRAINT `flight_attendants_assignment_ibfk_2` FOREIGN KEY (`attendant_id`) REFERENCES `flight_attendants` (`attendant_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `managers`
--

DROP TABLE IF EXISTS `managers`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `managers` (
  `manager_id` varchar(50) NOT NULL,
  `first_name_hebrew` varchar(50) NOT NULL,
  `last_name_hebrew` varchar(50) NOT NULL,
  `phone` varchar(15) DEFAULT NULL,
  `city` varchar(50) DEFAULT NULL,
  `street` varchar(50) DEFAULT NULL,
  `house_number` int DEFAULT NULL,
  `start_date` date NOT NULL,
  `manager_password` varchar(50) NOT NULL,
  PRIMARY KEY (`manager_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `pilots`
--

DROP TABLE IF EXISTS `pilots`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `pilots` (
  `pilot_id` varchar(50) NOT NULL,
  `first_name_hebrew` varchar(50) NOT NULL,
  `last_name_hebrew` varchar(50) NOT NULL,
  `phone` varchar(15) DEFAULT NULL,
  `city` varchar(50) DEFAULT NULL,
  `street` varchar(50) DEFAULT NULL,
  `house_number` int DEFAULT NULL,
  `start_date` date NOT NULL,
  `long_flight_certified` tinyint(1) NOT NULL,
  PRIMARY KEY (`pilot_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `pilots_assignment`
--

DROP TABLE IF EXISTS `pilots_assignment`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `pilots_assignment` (
  `flight_id` varchar(20) NOT NULL,
  `pilot_id` varchar(50) NOT NULL,
  PRIMARY KEY (`flight_id`,`pilot_id`),
  KEY `pilot_id` (`pilot_id`),
  CONSTRAINT `pilots_assignment_ibfk_1` FOREIGN KEY (`flight_id`) REFERENCES `flight` (`flight_id`),
  CONSTRAINT `pilots_assignment_ibfk_2` FOREIGN KEY (`pilot_id`) REFERENCES `pilots` (`pilot_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `registered_customer`
--

DROP TABLE IF EXISTS `registered_customer`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `registered_customer` (
  `email` varchar(100) NOT NULL,
  `passport_number` varchar(20) NOT NULL,
  `birth_date` date NOT NULL,
  `registration_date` date NOT NULL,
  `customer_password` varchar(100) NOT NULL,
  PRIMARY KEY (`email`),
  CONSTRAINT `registered_customer_ibfk_1` FOREIGN KEY (`email`) REFERENCES `customer` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `seat`
--

DROP TABLE IF EXISTS `seat`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `seat` (
  `aircraft_id` varchar(50) NOT NULL,
  `class_type` varchar(20) NOT NULL,
  `row_num` int NOT NULL,
  `column_letter` char(1) NOT NULL,
  PRIMARY KEY (`aircraft_id`,`class_type`,`row_num`,`column_letter`),
  CONSTRAINT `seat_ibfk_1` FOREIGN KEY (`aircraft_id`, `class_type`) REFERENCES `class` (`aircraft_id`, `class_type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `seats_in_flights`
--

DROP TABLE IF EXISTS `seats_in_flights`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `seats_in_flights` (
  `flight_id` varchar(20) NOT NULL,
  `aircraft_id` varchar(50) NOT NULL,
  `class_type` varchar(20) NOT NULL,
  `row_num` int NOT NULL,
  `column_letter` char(1) NOT NULL,
  `seat_status` varchar(10) DEFAULT NULL,
  PRIMARY KEY (`flight_id`,`aircraft_id`,`class_type`,`row_num`,`column_letter`),
  KEY `aircraft_id` (`aircraft_id`,`class_type`,`row_num`,`column_letter`),
  CONSTRAINT `seats_in_flights_ibfk_1` FOREIGN KEY (`flight_id`) REFERENCES `flight` (`flight_id`),
  CONSTRAINT `seats_in_flights_ibfk_2` FOREIGN KEY (`aircraft_id`, `class_type`, `row_num`, `column_letter`) REFERENCES `seat` (`aircraft_id`, `class_type`, `row_num`, `column_letter`),
  CONSTRAINT `seats_in_flights_chk_1` CHECK ((`seat_status` in (_utf8mb4'Available',_utf8mb4'Occupied')))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `selected_seats_in_booking`
--

DROP TABLE IF EXISTS `selected_seats_in_booking`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `selected_seats_in_booking` (
  `booking_id` varchar(50) NOT NULL,
  `aircraft_id` varchar(50) NOT NULL,
  `class_type` varchar(20) NOT NULL,
  `row_num` int NOT NULL,
  `column_letter` char(1) NOT NULL,
  PRIMARY KEY (`booking_id`,`aircraft_id`,`class_type`,`row_num`,`column_letter`),
  KEY `aircraft_id` (`aircraft_id`,`class_type`,`row_num`,`column_letter`),
  CONSTRAINT `selected_seats_in_booking_ibfk_1` FOREIGN KEY (`booking_id`) REFERENCES `booking` (`booking_id`),
  CONSTRAINT `selected_seats_in_booking_ibfk_2` FOREIGN KEY (`aircraft_id`, `class_type`, `row_num`, `column_letter`) REFERENCES `seat` (`aircraft_id`, `class_type`, `row_num`, `column_letter`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `unregistered_customer`
--

DROP TABLE IF EXISTS `unregistered_customer`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `unregistered_customer` (
  `email` varchar(100) NOT NULL,
  PRIMARY KEY (`email`),
  CONSTRAINT `unregistered_customer_ibfk_1` FOREIGN KEY (`email`) REFERENCES `customer` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2025-12-22 18:04:00
