"""Additional location-specific searches for submerged vegetation photographs."""
import expand_photo_library as library

library.AREAS=[
 ('eastasia','Japan','Akkeshi',43.04,144.84),('eastasia','Japan','Notsuke',43.57,145.28),
 ('eastasia','Japan','Shibetsu',43.66,145.13),('eastasia','Japan','Furen',43.27,145.33),
 ('eastasia','Japan','Sanbanze',35.67,139.94),('eastasia','Japan','Tokyo Bay',35.4,139.8),
 ('eastasia','Japan','Shizugawa',38.67,141.45),('eastasia','Japan','Matsushima',38.37,141.06),
 ('eastasia','Japan','Ishigaki',24.42,124.2),('eastasia','Japan','Kushimoto',33.47,135.78),
 ('eastasia','Japan','Okinawa',26.5,128.0),('eastasia','Japan','Hokkaido',43.1,144.0),
 ('eastasia','South Korea','Jeju',33.4,126.5),('eastasia','South Korea','Wando',34.31,126.76),
 ('eastasia','South Korea','Geoje',34.9,128.6),('eastasia','South Korea','Namhae',34.83,127.9),
 ('eastasia','Russia','Vladivostok',43.1,131.9),('eastasia','Russia','Sakhalin',48,142.5),
 ('eastasia','Philippines','Bolinao',16.38,119.89),('eastasia','Philippines','Puerto Galera',13.5,120.95),
 ('eastasia','Philippines','Coron',12,120.2),('eastasia','Philippines','Palawan',10,118.8),
 ('eastasia','Philippines','Bohol',9.8,124.15),('gulf','United Arab Emirates','Abu Dhabi',24.47,54.37),
 ('redsea','Egypt','Abu Dabbab',25.34,34.74),('redsea','Egypt','Marsa Alam',25.07,34.89),
]
library.SUBJECTS=[('kelp_macroalgae','kelp underwater'),('seagrass','seagrass'),('seagrass','eelgrass')]
library.DISCOVERY_TARGET=2500
if __name__=='__main__':library.discover()
