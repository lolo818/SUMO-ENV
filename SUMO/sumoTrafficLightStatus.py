"""
     |                       |         |
    ---         ---        --|         |--
                 |           |         |
 TJunction_n  TJunction_s  TJunction_w TJunction_e
"""

trafficLightStatus = {
    "TJunction": {
        "2_2_2": {
            "n": {
                "0": "rrGGGGGg",
                "0_yellow": "yyrrrrrr",
                "1": "GGrrrrrr",
                "1_yellow": "rryyyyyy",
            },
            "e": {
                "0": "rrrGGrrr",
                "0_yellow": "yyyrryyy",
                "1": "GGgrrGGG",
                "1_yellow": "rrryyrrr",
            },
            "s": {
                "0": "GGgrrGGG",
                "0_yellow": "rrryyrrr",
                "1": "rrrGGrrr",
                "1_yellow": "yyyrryyy",
            },
            "w": {
                "0": "rrrrrrGG",
                "0_yellow": "yyyyyyrr",
                "1": "GGGGGgrr",
                "1_yellow": "rrrrrryy",
            },
        }
    },
    "Junction": {
        "2_2_2_2": {
            "0": "rrrrGGGgrrrrGGGg",
            "0_yellow": "yyyyrrrryyyyrrrr",
            "1": "GGGgrrrrGGGgrrrr",
            "1_yellow": "rrrryyyyrrrryyyy",
        },
    },
}
