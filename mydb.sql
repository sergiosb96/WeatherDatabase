/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET NAMES utf8 */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;


CREATE DATABASE IF NOT EXISTS `NTUA` /*!40100 DEFAULT CHARACTER SET utf8mb4 */;
USE `NTUA`;

CREATE TABLE IF NOT EXISTS `cities` (
  `city_id` int(11) NOT NULL AUTO_INCREMENT,
  `active` int(1) NOT NULL DEFAULT 1,
  `name` varchar(255) NOT NULL,
  `lat` double NOT NULL,
  `lon` double NOT NULL,
  `tz` varchar(50) DEFAULT NULL,
  `country` varchar(255) DEFAULT NULL,
  `country_code` varchar(255) NOT NULL,
  `added` date NOT NULL,
  `started` date NOT NULL,
  `daily` int(1) DEFAULT 0,
  `hourly` int(1) DEFAULT 0,
  `icon` int(1) DEFAULT 0,
  `icon_15` int(1) DEFAULT 0,
  `gfs` int(1) DEFAULT 0,
  `meteofrance` int(1) DEFAULT 0,
  `comment` text DEFAULT NULL,
  PRIMARY KEY (`city_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3;

CREATE TABLE IF NOT EXISTS `parameters` (
  `source` varchar(255) DEFAULT NULL,
  `parameter` varchar(255) DEFAULT NULL,
  `units` varchar(255) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT IGNORE INTO `parameters` (`source`, `parameter`, `units`) VALUES
	('daily', 'temparature_max_C', '°C'),
	('daily', 'temparature_min_C', '°C'),
	('daily', 'wind_speed', 'km/h'),
	('daily', 'wind_direction', '°'),
	('daily', 'shortwave_radiation_sum', 'MJ/m²'),
	('hourly', 'temperature', '°C'),
	('hourly', 'humidity', '%'),
	('hourly', 'windspeed_10m', 'km/h'),
	('hourly', 'windspeed_80m', 'km/h'),
	('hourly', 'windspeed_120m', 'km/h'),
	('hourly', 'windspeed_180m', 'km/h'),
	('hourly', 'winddirection_10m', '°'),
	('hourly', 'winddirection_80m', '°'),
	('hourly', 'winddirection_120m', '°'),
	('hourly', 'winddirection_180m', '°'),
	('hourly', 'temperature_80m', '°C'),
	('hourly', 'temperature_120m', '°C'),
	('hourly', 'temperature_180m', '°C'),
	('hourly', 'shortwave_radiation', 'W/m²'),
	('hourly', 'direct_radiation', 'W/m²'),
	('hourly', 'diffuse_radiation', 'W/m²'),
	('icon_15', 'shortwave_radiation', 'W/m²'),
	('icon_15', 'direct_radiation', 'W/m²'),
	('icon_15', 'diffuse_radiation', 'W/m²'),
	('icon_15', 'direct_normal_irradiance', 'W/m²'),
	('icon_15', 'terrestrial_radiation', 'W/m²'),
	('meteofrance', 'temperature', '°C'),
	('meteofrance', 'humidity', '%'),
	('meteofrance', 'windspeed_10m', 'km/h'),
	('meteofrance', 'winddirection_10m', '°'),
	('meteofrance', 'windgusts_10m', 'km/h'),
	('meteofrance', 'shortwave_radiation', 'W/m²'),
	('meteofrance', 'direct_radiation', 'W/m²'),
	('meteofrance', 'diffuse_radiation', 'W/m²'),
	('meteofrance', 'direct_normal_irradiance', 'W/m²'),
	('meteofrance', 'terrestrial_radiation', 'W/m²'),
	('icon', 'temperature', '°C'),
	('icon', 'humidity', '%'),
	('icon', 'windspeed_10m', 'km/h'),
	('icon', 'windspeed_80m', 'km/h'),
	('icon', 'windspeed_120m', 'km/h'),
	('icon', 'windspeed_180m', 'km/h'),
	('icon', 'winddirection_10m', '°'),
	('icon', 'winddirection_80m', '°'),
	('icon', 'winddirection_120m', '°'),
	('icon', 'winddirection_180m', '°'),
	('icon', 'windgusts_10m', 'km/h'),
	('icon', 'temperature_80m', '°C'),
	('icon', 'temperature_120m', '°C'),
	('icon', 'temperature_180m', '°C'),
	('icon', 'shortwave_radiation', 'W/m²'),
	('icon', 'direct_radiation', 'W/m²'),
	('icon', 'diffuse_radiation', 'W/m²'),
	('icon', 'direct_normal_irradiance', 'W/m²'),
	('icon', 'terrestrial_radiation', 'W/m²'),
	('gfs', 'temperature', '°C'),
	('gfs', 'humidity', '%'),
	('gfs', 'windspeed_10m', 'km/h'),
	('gfs', 'windspeed_80m', 'km/h'),
	('gfs', 'winddirection_10m', '°'),
	('gfs', 'winddirection_80m', '°'),
	('gfs', 'windgusts_10m', 'km/h'),
	('gfs', 'shortwave_radiation', 'W/m²'),
	('gfs', 'direct_radiation', 'W/m²'),
	('gfs', 'diffuse_radiation', 'W/m²'),
	('gfs', 'direct_normal_irradiance', 'W/m²'),
	('gfs', 'terrestrial_radiation', 'W/m²');

CREATE TABLE IF NOT EXISTS `query_urls` (
  `query_urls_id` int(11) NOT NULL AUTO_INCREMENT,
  `city_id` int(11) DEFAULT NULL,
  `daily` longtext DEFAULT NULL,
  `hourly` longtext DEFAULT NULL,
  `icon` longtext DEFAULT NULL,
  `icon_15` longtext DEFAULT NULL,
  `gfs` longtext DEFAULT NULL,
  `meteofrance` longtext DEFAULT NULL,
  PRIMARY KEY (`query_urls_id`),
  KEY `query_urls_ibfk_1` (`city_id`),
  CONSTRAINT `query_urls_ibfk_1` FOREIGN KEY (`city_id`) REFERENCES `cities` (`city_id`) ON DELETE CASCADE,
  CONSTRAINT `query_urls_ibfk_2` FOREIGN KEY (`city_id`) REFERENCES `cities` (`city_id`) ON DELETE CASCADE,
  CONSTRAINT `query_urls_ibfk_3` FOREIGN KEY (`city_id`) REFERENCES `cities` (`city_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `urls` (
  `daily` varchar(250) DEFAULT NULL,
  `hourly` varchar(250) DEFAULT NULL,
  `icon` varchar(250) DEFAULT NULL,
  `gfs` varchar(250) DEFAULT NULL,
  `meteofrance` varchar(250) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT IGNORE INTO `urls` (`daily`, `hourly`, `icon`, `gfs`, `meteofrance`) VALUES
	('https://open-meteo.com/en/docs', 'https://open-meteo.com/en/docs', 'https://open-meteo.com/en/docs/dwd-api', 'https://open-meteo.com/en/docs/gfs-api', 'https://open-meteo.com/en/docs/meteofrance-api');

/*!40103 SET TIME_ZONE=IFNULL(@OLD_TIME_ZONE, 'system') */;
/*!40101 SET SQL_MODE=IFNULL(@OLD_SQL_MODE, '') */;
/*!40014 SET FOREIGN_KEY_CHECKS=IFNULL(@OLD_FOREIGN_KEY_CHECKS, 1) */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40111 SET SQL_NOTES=IFNULL(@OLD_SQL_NOTES, 1) */;
