# uoa-poc2-controller
A FIWARE application to controller autonomous mobile robots

[![TravisCI Status](https://travis-ci.org/RoboticBase/uoa-poc2-controller.svg?branch=master)](https://travis-ci.org/RoboticBase/uoa-poc2-controller)

## Description
This [FIWARE](https://www.fiware.org/) component controls autonomous mobile robots as a kind of IoT devices by using [FIWARE-Orion](https://fiware-orion.readthedocs.io/) and [FIWARE-IoTAgent-json](https://fiware-iotagent-json.readthedocs.io/).

This application was used in a PoC demonstrated by TIS and UoA in November 2019.

## Requirements

* python 3.7 or higher

## Environment Variables
This application accepts some Environment Variables like below:

|Environment Variable|Summary|Mandatory|Default|
|:--|:--|:--|:--|
|`LOG_LEVEL`|log level(DEBUG, INFO, WARNING, ERRRO, CRITICAL)|||
|`LISTEN_PORT`|listen port of this service|YES|3000|
|`TIMEZONE`|timezone|YES|UTC|
|`ORION_ENDPOINT`|endpoint url of orion context broker|YES||
|`ORION_TOKEN`|bearer token of orion context broker|||
|`FIWARE_SERVICE`|the value of 'Fiware-Service' HTTP Header|YES||
|`DELIVERY_ROBOT_SERVICEPATH`|the value of 'Fiware-Servicepath' HTTP Header for mobile robots|YES||
|`DELIVERY_ROBOT_TYPE`|the NGSI type of mobile robots|YES||
|`DELIVERY_ROBOT_LIST`|the list of NGSI id of mobile robots (JSON format string)|YES||
|`ROBOT_UI_SERVICEPATH`|the value of 'Fiware-Servicepath' HTTP Header for mobile robot UIs|YES||
|`ROBOT_UI_TYPE`|the NGSI type of mobile robot UIs|YES||
|`ID_TABLE`|the dictionary of mobile robot id to mobile robot UI id|YES||
|`TOKEN_SERVICEPATH`|the value of 'Fiware-Servicepath' HTTP Header for token objects|YES||
|`TOKEN_TYPE`|the NGSI type of token objects|YES||
|`CORS_ORIGINS`|the value of CORS origin like "\*"|||
|`MOVENEXT_WAIT_MSEC`|the wait time (micro seconds) checking the result of a command sent to a mobile robot|YES|200|
|`MOVENEXT_WAIT_MAX_NUM`|the max count checking the result of a command sent to a mobile robot|YES|25|
|`NOTIFICATION_THROTTLING_MSEC`|the throttling time (micro seconds) of messages notifed from FIWARE-Orion|YES|500|
|`MONGODB_HOST`|mongodb hostname to store lock objects|YES||
|`MONGODB_PORT`|mongodb port to store lock objects|YES||
|`MONGODB_REPLICASET`|mongodb replicaset to store lock objects|YES||
|`MONGODB_DB_NAME`|mongodb database name to store lock objects|YES||
|`MONGODB_COLLECTION_NAME`|mongodb collection name to store lock objects|YES||

## License

[Apache License 2.0](/LICENSE)

## Copyright
Copyright (c) 2019 [TIS Inc.](https://www.tis.co.jp/)
