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
  `aircraft_id` int NOT NULL AUTO_INCREMENT,
  `manufacturer` varchar(20) NOT NULL,
  `size` varchar(30) NOT NULL,
  `purchase_date` date DEFAULT NULL,
  PRIMARY KEY (`aircraft_id`),
  CONSTRAINT `aircraft_chk_1` CHECK ((`manufacturer` in (_utf8mb4'Boeing',_utf8mb4'Airbus',_utf8mb4'Dassault'))),
  CONSTRAINT `aircraft_chk_2` CHECK ((`size` in (_utf8mb4'Large',_utf8mb4'Small')))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `aircraft`
--

LOCK TABLES `aircraft` WRITE;
/*!40000 ALTER TABLE `aircraft` DISABLE KEYS */;
/*!40000 ALTER TABLE `aircraft` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `booking`
--

DROP TABLE IF EXISTS `booking`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `booking` (
  `booking_id` int NOT NULL AUTO_INCREMENT,
  `customer_email` varchar(100) NOT NULL,
  `flight_id` int NOT NULL,
  `booking_date` date DEFAULT NULL,
  `booking_status` varchar(50) NOT NULL,
  `payment` decimal(10,2) DEFAULT '0.00',
  PRIMARY KEY (`booking_id`),
  KEY `flight_id` (`flight_id`),
  CONSTRAINT `booking_ibfk_2` FOREIGN KEY (`flight_id`) REFERENCES `flight` (`flight_id`),
  CONSTRAINT `booking_chk_1` CHECK ((`booking_status` in (_utf8mb4'Active',_utf8mb4'Completed',_utf8mb4'Customer Cancellation',_utf8mb4'System Cancellation')))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `booking`
--

LOCK TABLES `booking` WRITE;
/*!40000 ALTER TABLE `booking` DISABLE KEYS */;
/*!40000 ALTER TABLE `booking` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `class`
--

DROP TABLE IF EXISTS `class`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `class` (
  `aircraft_id` int NOT NULL,
  `class_type` varchar(20) NOT NULL,
  `num_rows` int DEFAULT NULL,
  `num_columns` int DEFAULT NULL,
  PRIMARY KEY (`aircraft_id`,`class_type`),
  CONSTRAINT `class_ibfk_1` FOREIGN KEY (`aircraft_id`) REFERENCES `aircraft` (`aircraft_id`),
  CONSTRAINT `class_chk_1` CHECK ((`class_type` in (_utf8mb4'economy',_utf8mb4'business')))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `class`
--

LOCK TABLES `class` WRITE;
/*!40000 ALTER TABLE `class` DISABLE KEYS */;
/*!40000 ALTER TABLE `class` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `classes_in_flight`
--

DROP TABLE IF EXISTS `classes_in_flight`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `classes_in_flight` (
  `flight_id` int NOT NULL,
  `aircraft_id` int NOT NULL,
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
-- Dumping data for table `classes_in_flight`
--

LOCK TABLES `classes_in_flight` WRITE;
/*!40000 ALTER TABLE `classes_in_flight` DISABLE KEYS */;
/*!40000 ALTER TABLE `classes_in_flight` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `flight`
--

DROP TABLE IF EXISTS `flight`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `flight` (
  `flight_id` int NOT NULL AUTO_INCREMENT,
  `flight_status` varchar(20) NOT NULL,
  `departure_time` time NOT NULL,
  `departure_date` date NOT NULL,
  `origin_airport` varchar(10) NOT NULL,
  `destination_airport` varchar(10) NOT NULL,
  `aircraft_id` int NOT NULL,
  PRIMARY KEY (`flight_id`),
  KEY `aircraft_id` (`aircraft_id`),
  KEY `origin_airport` (`origin_airport`,`destination_airport`),
  CONSTRAINT `flight_ibfk_1` FOREIGN KEY (`aircraft_id`) REFERENCES `aircraft` (`aircraft_id`),
  CONSTRAINT `flight_ibfk_2` FOREIGN KEY (`origin_airport`, `destination_airport`) REFERENCES `routes` (`origin_airport`, `destination_airport`),
  CONSTRAINT `flight_chk_1` CHECK ((`flight_status` in (_utf8mb4'Active',_utf8mb4'Fully Booked',_utf8mb4'Completed',_utf8mb4'Cancelled')))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `flight`
--

LOCK TABLES `flight` WRITE;
/*!40000 ALTER TABLE `flight` DISABLE KEYS */;
/*!40000 ALTER TABLE `flight` ENABLE KEYS */;
UNLOCK TABLES;

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
-- Dumping data for table `flight_attendants`
--

LOCK TABLES `flight_attendants` WRITE;
/*!40000 ALTER TABLE `flight_attendants` DISABLE KEYS */;
/*!40000 ALTER TABLE `flight_attendants` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `flight_attendants_assignment`
--

DROP TABLE IF EXISTS `flight_attendants_assignment`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `flight_attendants_assignment` (
  `flight_id` int NOT NULL,
  `attendant_id` varchar(50) NOT NULL,
  PRIMARY KEY (`flight_id`,`attendant_id`),
  KEY `attendant_id` (`attendant_id`),
  CONSTRAINT `flight_attendants_assignment_ibfk_1` FOREIGN KEY (`flight_id`) REFERENCES `flight` (`flight_id`),
  CONSTRAINT `flight_attendants_assignment_ibfk_2` FOREIGN KEY (`attendant_id`) REFERENCES `flight_attendants` (`attendant_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `flight_attendants_assignment`
--

LOCK TABLES `flight_attendants_assignment` WRITE;
/*!40000 ALTER TABLE `flight_attendants_assignment` DISABLE KEYS */;
/*!40000 ALTER TABLE `flight_attendants_assignment` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `guest_customer`
--

DROP TABLE IF EXISTS `guest_customer`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `guest_customer` (
  `email` varchar(100) NOT NULL,
  `first_name_english` varchar(50) NOT NULL,
  `last_name_english` varchar(50) NOT NULL,
  PRIMARY KEY (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `guest_customer`
--

LOCK TABLES `guest_customer` WRITE;
/*!40000 ALTER TABLE `guest_customer` DISABLE KEYS */;
INSERT INTO `guest_customer` VALUES ('eladi.levy@gmail.com','elad','levy');
/*!40000 ALTER TABLE `guest_customer` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `guest_customer_phones`
--

DROP TABLE IF EXISTS `guest_customer_phones`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `guest_customer_phones` (
  `email` varchar(100) NOT NULL,
  `phone_number` varchar(15) NOT NULL,
  PRIMARY KEY (`email`,`phone_number`),
  CONSTRAINT `guest_phone_ibfk_1` FOREIGN KEY (`email`) REFERENCES `guest_customer` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `guest_customer_phones`
--

LOCK TABLES `guest_customer_phones` WRITE;
/*!40000 ALTER TABLE `guest_customer_phones` DISABLE KEYS */;
INSERT INTO `guest_customer_phones` VALUES ('eladi.levy@gmail.com','0508672366');
/*!40000 ALTER TABLE `guest_customer_phones` ENABLE KEYS */;
UNLOCK TABLES;

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
-- Dumping data for table `managers`
--

LOCK TABLES `managers` WRITE;
/*!40000 ALTER TABLE `managers` DISABLE KEYS */;
INSERT INTO `managers` VALUES ('admin1','משה','לוי',NULL,NULL,NULL,NULL,'2020-01-01','admin123');
/*!40000 ALTER TABLE `managers` ENABLE KEYS */;
UNLOCK TABLES;

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
-- Dumping data for table `pilots`
--

LOCK TABLES `pilots` WRITE;
/*!40000 ALTER TABLE `pilots` DISABLE KEYS */;
INSERT INTO `pilots` VALUES ('345','משה','לוי','0528194007','Savyon','Salit',6,'2026-01-03',1);
/*!40000 ALTER TABLE `pilots` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `pilots_assignment`
--

DROP TABLE IF EXISTS `pilots_assignment`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `pilots_assignment` (
  `flight_id` int NOT NULL,
  `pilot_id` varchar(50) NOT NULL,
  PRIMARY KEY (`flight_id`,`pilot_id`),
  KEY `pilot_id` (`pilot_id`),
  CONSTRAINT `pilots_assignment_ibfk_1` FOREIGN KEY (`flight_id`) REFERENCES `flight` (`flight_id`),
  CONSTRAINT `pilots_assignment_ibfk_2` FOREIGN KEY (`pilot_id`) REFERENCES `pilots` (`pilot_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `pilots_assignment`
--

LOCK TABLES `pilots_assignment` WRITE;
/*!40000 ALTER TABLE `pilots_assignment` DISABLE KEYS */;
/*!40000 ALTER TABLE `pilots_assignment` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `registered_customer`
--

DROP TABLE IF EXISTS `registered_customer`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `registered_customer` (
  `email` varchar(100) NOT NULL,
  `first_name_english` varchar(50) NOT NULL,
  `last_name_english` varchar(50) NOT NULL,
  `passport_number` varchar(20) NOT NULL,
  `birth_date` date NOT NULL,
  `registration_date` date NOT NULL,
  `customer_password` varchar(100) NOT NULL,
  PRIMARY KEY (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `registered_customer`
--

LOCK TABLES `registered_customer` WRITE;
/*!40000 ALTER TABLE `registered_customer` DISABLE KEYS */;
INSERT INTO `registered_customer` VALUES ('drorz@levitansharon.co.il','Dror','Zamir','123456','2002-05-07','2026-01-03','Drorzamir'),('Galicaspi@g.com','gali','caspi','1111111','1998-11-07','2026-01-05','123456'),('mau@gmail.com','mau','zamir','1245677','2002-05-27','2026-01-05','087645'),('mayzamir@gmail.com','may','zamir','123456','2002-05-27','2025-12-31','mayzamir'),('mjn@gmai.com','msh','nd','1245677','2000-05-04','2026-01-05','123666'),('sara@gmail.com','sara','zamir','56789','1970-01-26','2025-12-31','saraza');
/*!40000 ALTER TABLE `registered_customer` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `registered_customer_phones`
--

DROP TABLE IF EXISTS `registered_customer_phones`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `registered_customer_phones` (
  `email` varchar(100) NOT NULL,
  `phone_number` varchar(15) NOT NULL,
  PRIMARY KEY (`email`,`phone_number`),
  CONSTRAINT `reg_phone_ibfk_1` FOREIGN KEY (`email`) REFERENCES `registered_customer` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `registered_customer_phones`
--

LOCK TABLES `registered_customer_phones` WRITE;
/*!40000 ALTER TABLE `registered_customer_phones` DISABLE KEYS */;
INSERT INTO `registered_customer_phones` VALUES ('drorz@levitansharon.co.il','0546656097'),('Galicaspi@g.com','0099887766'),('Galicaspi@g.com','123456789'),('mau@gmail.com','0528194007'),('mau@gmail.com','0987655454'),('mayzamir@gmail.com','0528194007'),('mjn@gmai.com','0987655454'),('sara@gmail.com','0508672366');
/*!40000 ALTER TABLE `registered_customer_phones` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `routes`
--

DROP TABLE IF EXISTS `routes`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `routes` (
  `origin_airport` varchar(10) NOT NULL,
  `destination_airport` varchar(10) NOT NULL,
  `flight_duration_mins` int DEFAULT NULL,
  PRIMARY KEY (`origin_airport`,`destination_airport`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `routes`
--

LOCK TABLES `routes` WRITE;
/*!40000 ALTER TABLE `routes` DISABLE KEYS */;
INSERT INTO `routes` VALUES ('TLV','CDG',300),('TLV','JFK',720);
/*!40000 ALTER TABLE `routes` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `seat`
--

DROP TABLE IF EXISTS `seat`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `seat` (
  `aircraft_id` int NOT NULL,
  `class_type` varchar(20) NOT NULL,
  `row_num` int NOT NULL,
  `column_letter` char(1) NOT NULL,
  PRIMARY KEY (`aircraft_id`,`class_type`,`row_num`,`column_letter`),
  CONSTRAINT `seat_ibfk_1` FOREIGN KEY (`aircraft_id`, `class_type`) REFERENCES `class` (`aircraft_id`, `class_type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `seat`
--

LOCK TABLES `seat` WRITE;
/*!40000 ALTER TABLE `seat` DISABLE KEYS */;
/*!40000 ALTER TABLE `seat` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `selected_seats_in_booking`
--

DROP TABLE IF EXISTS `selected_seats_in_booking`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `selected_seats_in_booking` (
  `booking_id` int NOT NULL,
  `aircraft_id` int NOT NULL,
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
-- Dumping data for table `selected_seats_in_booking`
--

LOCK TABLES `selected_seats_in_booking` WRITE;
/*!40000 ALTER TABLE `selected_seats_in_booking` DISABLE KEYS */;
/*!40000 ALTER TABLE `selected_seats_in_booking` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-01-05 11:33:24
