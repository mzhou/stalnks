#!/usr/bin/env python3

import cfg
import stalnks

png = stalnks.run_prediction(cfg.PAGE_URL, [100, 0, 0, 0, 20, 0, 0, 56, 70, 0, 0, 0, 0])
with open('test.png', 'wb') as f:
    f.write(png)
