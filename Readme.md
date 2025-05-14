# Black forest hackathon 2025: Challenge 5, Badenova Netze
A small writeup of our experience at the Black forest hackathon 2025.

Utility providers like Badenova Netze face an investment uncertainty:
For an electricity network it is unknown how and especially where power demand will rise in the future,
possibly stressing supply infrastructure like transformer stations in the network.

Our goal for this hackathon was to predict solar cell, heatpump and ev charging infrastructure installations.
After tackling with the provided data (which is not included in this repository) for some time we concluded to focus
on PV installations. They can to some degree compensate other new high-power appliances like ev chargers or heatpumps.

The provided data included a dataset by Nexiga for demographic / consumer data at the household level,
with datapoints like income, income category, attitude towards electric mobility and others.

Additional Badenova-Netze internal data included a set of PV installations of the region
(with geolocation, peak power, installation / registration date) as well as heatpump installs
(only with an address and install date). We mapped both PV and heatpump data to the coordinates of a street-level
address provided by the state of Baden-Wuerttemberg (https://www.lgl-bw.de/Produkte/Liegenschaftskataster/ALKIS/).
For mapping a PV installation to a nexiga datapoint, we used the h3 library with a varying resolution.

Our team member David was able to use xgboost to predict whether a PV installation will occur,
for a given year, per h3 cell.
We then used these values to calculate the feature importance and get a rough impression of the quality of our
prediction using the F1 score.