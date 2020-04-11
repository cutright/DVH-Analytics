// Scripts by Dan Cutright, PhD
// Northwestern Medicine
// March 30, 2017
// Notes for POI-generation scripts

Both of the following scripts are required for expected functionality:
DVH-Analytics_Create-POIs.Script.p3rtp
DVH-Analytics_Create-Rx-POI.Script.p3rtp

Alternatively, you can manually create POIs in the same format.

A POI in the format:
"tx: <site>"
will allow DVH-Analytics to add this site name to the database upon import.

A POI in the format:
"rx#: <rx name>: <rx dose in cGy> cGy x <fxs> to <normalization %>%: <normalization method>: <normalization object>"
where # is rx number starting from 1, will allow DVH-Analytics to retrieve rx information.
