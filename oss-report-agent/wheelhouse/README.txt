Place offline Python wheels here for air-gapped builds.

Populate this directory from an internet-connected host:

pip download -r requirements.txt -d wheelhouse

Then transfer this folder into the air-gapped environment before docker build.
