CREATE DATABASE  IF NOT EXISTS `1ctg` /*!40100 DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci */ /*!80016 DEFAULT ENCRYPTION='N' */;
USE `1ctg`;
-- MySQL dump 10.13  Distrib 8.0.45, for Win64 (x86_64)
--
-- Host: 127.0.0.1    Database: 1ctg
-- ------------------------------------------------------
-- Server version	8.0.45

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
-- Table structure for table `bookings`
--

DROP TABLE IF EXISTS `bookings`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `bookings` (
  `id` int NOT NULL AUTO_INCREMENT,
  `client_name` varchar(255) DEFAULT NULL,
  `quest_name` varchar(255) DEFAULT NULL,
  `date` date DEFAULT NULL,
  `time_start` time DEFAULT NULL,
  `time_end` time DEFAULT NULL,
  `processed` tinyint(1) DEFAULT '0',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=15 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `bookings`
--

LOCK TABLES `bookings` WRITE;
/*!40000 ALTER TABLE `bookings` DISABLE KEYS */;
INSERT INTO `bookings` VALUES (1,'Шкарпицкий Александр Николаевич','Корабль-призрак','2026-04-18','12:00:00','14:00:00',2),(2,'Наумов Данила Игоревич','Тайна Шерлока','2026-04-18','16:00:00','17:30:00',2),(3,'Наумов Данила Игоревич','Двойная жизнь','2026-04-14','12:00:00','13:00:00',2),(4,'Наумов Данила Игоревич','Проклятый дом','2026-04-18','22:00:00','23:00:00',2),(5,'Шкарпицкий Александр Николаевич','Корабль-призрак','2026-04-15','10:00:00','12:00:00',2),(6,'Шкарпицкий Александр Николаевич','Крёстный отец','2026-04-17','12:00:00','13:00:00',2),(7,'Шкарпицкий Александр Николаевич','Крёстный отец','2026-04-16','12:00:00','13:00:00',2),(8,'Шкарпицкий Александр Николаевич','Проклятый дом','2026-04-17','16:00:00','17:00:00',2),(9,'Шкарпицкий Александр Николаевич','Корабль-призрак','2026-04-18','18:00:00','20:00:00',2),(10,'Шкарпицкий Александр Николаевич','Корабль-призрак','2026-04-17','20:00:00','22:00:00',2),(11,'Наумов Данила Игоревич','Проклятый дом','2026-04-19','18:00:00','19:00:00',2),(12,'Наумов Данила Игоревич','Тайна Шерлока','2026-04-20','22:00:00','23:30:00',2),(13,'Наумов Данила Игоревич','Корабль-призрак','2026-04-18','22:00:00','00:00:00',1),(14,'Кокорев Алексей Евгеньевич','Крёстный отец','2026-04-18','12:00:00','13:00:00',2);
/*!40000 ALTER TABLE `bookings` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-04-13 19:43:41
