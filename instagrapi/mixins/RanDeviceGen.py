from faker import Faker
import random

class DeviceGen:


    def random_device():
        
        # Create a Faker instance
        fake = Faker()

        # Generate fake device information
        # app_version = fake.numerify(text="###.###.###.###")
        # Version = fake.random_int(min=21, max=30)

        # Define a dictionary mapping Android versions to their corresponding releases
        android_releases = {
            
            5: random.choice(["5.0.0", "5.1.0"]),
            6: "6.0.0",
            7: random.choice(["7.0.0", "7.1.0"]),
            8: random.choice(["8.0.0", "8.1.0"]),
            9: "9.0.0",
            10: "10.0.0",
            11: "11.0.0",
            12: "11.0.0",

        }

        # Select the corresponding release based on the generated Android version
        # android_release = android_releases.get(Version)


        app_versions = {
            
            
            "7.0.0": ['322.0.0.37.95', '322.0.0.37.95', '322.0.0.37.95', '321.0.0.39.106', '321.0.0.39.106',
                        '320.0.0.42.101', '319.0.0.43.110', '319.0.0.43.110', '319.0.0.43.110', '318.0.0.30.110',
                        '317.0.0.34.109', '316.0.0.38.109', '315.0.0.29.109', '314.0.0.20.114', '314.0.0.14.114',
                        '313.0.0.26.328', '313.0.0.26.328', '312.1.0.34.111', '311.0.0.32.118', '310.0.0.37.328',
                        '309.1.0.41.113', '309.0.0.40.113', '309.0.0.40.113', '308.0.0.36.109', '308.0.0.36.109',
                        '307.0.0.34.111', '306.0.0.35.109', '306.0.0.35.109', '305.0.0.34.110', '304.0.0.35.106',
                        '303.0.0.40.109', '302.1.0.36.111', '302.1.0.36.111', '302.0.0.34.111', '301.1.0.33.110',
                        '301.0.0.33.110', '300.0.0.29.110', '300.0.0.29.110', '300.0.0.0.44', '299.0.0.34.111',
                        '298.0.0.31.110', '298.0.0.31.110', '297.0.0.33.109', '297.0.0.33.109', '296.0.0.35.109',
                        '295.0.0.32.109', '294.0.0.33.87', '293.0.2.28.93', '293.0.2.28.93', '292.0.0.31.110',
                        '292.0.0.18.110', '291.1.0.34.111', '291.1.0.34.111', '290.0.0.13.76', '289.0.0.25.49',
                        '289.0.0.25.49', '288.1.0.22.66', '287.0.0.25.77', '286.0.0.20.69', '286.0.0.20.69',
                        '285.0.0.25.62', '284.0.0.22.85', '283.0.0.20.105', '283.0.0.20.105', '282.0.0.22.119',
                        '281.0.0.19.105', '280.0.0.18.114', '280.0.0.18.114', '279.0.0.23.112', '279.0.0.23.112',
                        '279.0.0.18.112'
                        ],

            "7.1.0": ['322.0.0.37.95', '322.0.0.37.95', '322.0.0.37.95', '321.0.0.39.106', '321.0.0.39.106',
                        '320.0.0.42.101', '319.0.0.43.110', '319.0.0.43.110', '319.0.0.43.110', '318.0.0.30.110',
                        '317.0.0.34.109', '316.0.0.38.109', '315.0.0.29.109', '314.0.0.20.114', '314.0.0.14.114',
                        '313.0.0.26.328', '313.0.0.26.328', '312.1.0.34.111', '311.0.0.32.118', '310.0.0.37.328',
                        '309.1.0.41.113', '309.0.0.40.113', '309.0.0.40.113', '308.0.0.36.109', '308.0.0.36.109',
                        '307.0.0.34.111', '306.0.0.35.109', '306.0.0.35.109', '305.0.0.34.110', '304.0.0.35.106',
                        '303.0.0.40.109', '302.1.0.36.111', '302.1.0.36.111', '302.0.0.34.111', '301.1.0.33.110',
                        '301.0.0.33.110', '300.0.0.29.110', '300.0.0.29.110', '300.0.0.0.44', '299.0.0.34.111',
                        '298.0.0.31.110', '298.0.0.31.110', '297.0.0.33.109', '297.0.0.33.109', '296.0.0.35.109',
                        '295.0.0.32.109', '294.0.0.33.87', '293.0.2.28.93', '293.0.2.28.93', '292.0.0.31.110',
                        '292.0.0.18.110', '291.1.0.34.111', '291.1.0.34.111', '290.0.0.13.76', '289.0.0.25.49',
                        '289.0.0.25.49', '288.1.0.22.66', '287.0.0.25.77', '286.0.0.20.69', '286.0.0.20.69',
                        '285.0.0.25.62', '284.0.0.22.85', '283.0.0.20.105', '283.0.0.20.105', '282.0.0.22.119',
                        '281.0.0.19.105', '280.0.0.18.114', '280.0.0.18.114', '279.0.0.23.112', '279.0.0.23.112',
                        '279.0.0.18.112'
                        ], 

            "6.0.0": ['253.0.0.17.114', '252.0.0.10.111', '247.0.0.11.113'],

            "5.0.0": ['278.0.0.22.117', '278.0.0.21.117', '277.0.0.17.107', '277.0.0.17.107', '276.1.0.26.103',
                        '276.0.0.26.103', '275.0.0.27.98', '274.0.0.26.90', '273.1.0.16.72', '273.0.0.16.72',
                        '272.0.0.16.73', '271.1.0.21.84', '271.0.0.20.84', '270.2.0.24.82', '270.0.0.23.82',
                        '269.0.0.18.75', '268.0.0.18.72', '267.0.0.18.93', '266.0.0.19.106', '265.0.0.19.301',
                        '265.0.0.19.301', '264.0.0.22.106', '264.0.0.0.99', '263.2.0.19.104', '263.0.0.19.104',
                        '262.0.0.24.327', '261.0.0.21.111', '260.0.0.23.115', '259.1.0.29.104', '259.0.0.29.104', 
                        '258.1.0.26.100', '258.0.0.26.100', '257.1.0.16.110', '257.0.0.16.110', '256.0.0.18.105',
                        '255.1.0.17.102', '254.0.0.19.109', '253.0.0.23.114', '253.0.0.20.114', '252.0.0.17.111',
                        '251.1.0.11.106', '251.0.0.11.106', '250.0.0.21.109', '249.0.0.20.105', '248.0.0.17.109',
                        '247.0.0.17.113', '246.0.0.16.113', '245.0.0.18.108'
                        ],

            "5.1.0": ['278.0.0.22.117', '278.0.0.21.117', '277.0.0.17.107', '277.0.0.17.107', '276.1.0.26.103',
                        '276.0.0.26.103', '275.0.0.27.98', '274.0.0.26.90', '273.1.0.16.72', '273.0.0.16.72',
                        '272.0.0.16.73', '271.1.0.21.84', '271.0.0.20.84', '270.2.0.24.82', '270.0.0.23.82',
                        '269.0.0.18.75', '268.0.0.18.72', '267.0.0.18.93', '266.0.0.19.106', '265.0.0.19.301',
                        '265.0.0.19.301', '264.0.0.22.106', '264.0.0.0.99', '263.2.0.19.104', '263.0.0.19.104',
                        '262.0.0.24.327', '261.0.0.21.111', '260.0.0.23.115', '259.1.0.29.104', '259.0.0.29.104', 
                        '258.1.0.26.100', '258.0.0.26.100', '257.1.0.16.110', '257.0.0.16.110', '256.0.0.18.105',
                        '255.1.0.17.102', '254.0.0.19.109', '253.0.0.23.114', '253.0.0.20.114', '252.0.0.17.111',
                        '251.1.0.11.106', '251.0.0.11.106', '250.0.0.21.109', '249.0.0.20.105', '248.0.0.17.109',
                        '247.0.0.17.113', '246.0.0.16.113', '245.0.0.18.108'
                        ],

            "9.0.0": ['313.0.0.0.263', '301.0.0.28.110', '301.0.0.27.110', '300.0.0.29.110', '294.0.4.0.15',
                        '293.0.2.0.28', '293.0.2.0.20', '293.0.2.0.11', '293.0.2.0.6', '292.0.0.26.110',
                        '292.0.0.18.110', '292.0.0.16.110', '283.0.0.20.105', '274.0.0.21.90', '269.0.0.14.75',
                        '268.0.0.13.72', '268.0.0.9.72', '265.0.0.1.301', '259.0.0.16.104'],
            
            
            "8.0.0": ['313.0.0.0.263', '301.0.0.28.110', '301.0.0.27.110', '300.0.0.29.110', '294.0.4.0.15',
                        '293.0.2.0.28', '293.0.2.0.20', '293.0.2.0.11', '293.0.2.0.6', '292.0.0.26.110',
                        '292.0.0.18.110', '292.0.0.16.110', '283.0.0.20.105', '274.0.0.21.90', '269.0.0.14.75',
                        '268.0.0.13.72', '268.0.0.9.72', '265.0.0.1.301', '259.0.0.16.104'],

            "8.1.0": ['313.0.0.0.263', '301.0.0.28.110', '301.0.0.27.110', '300.0.0.29.110', '294.0.4.0.15',
                        '293.0.2.0.28', '293.0.2.0.20', '293.0.2.0.11', '293.0.2.0.6', '292.0.0.26.110',
                        '292.0.0.18.110', '292.0.0.16.110', '283.0.0.20.105', '274.0.0.21.90', '269.0.0.14.75',
                        '268.0.0.13.72', '268.0.0.9.72', '265.0.0.1.301', '259.0.0.16.104'],

            "10.0.0": ['313.0.0.0.263', '301.0.0.28.110', '301.0.0.27.110', '300.0.0.29.110', '294.0.4.0.15',
                        '293.0.2.0.28', '293.0.2.0.20', '293.0.2.0.11', '293.0.2.0.6', '292.0.0.26.110',
                        '292.0.0.18.110', '292.0.0.16.110', '283.0.0.20.105', '274.0.0.21.90', '269.0.0.14.75',
                        '268.0.0.13.72', '268.0.0.9.72', '265.0.0.1.301', '259.0.0.16.104'],

            "11.0.0": ['313.0.0.0.263', '301.0.0.28.110', '301.0.0.27.110', '300.0.0.29.110', '294.0.4.0.15',
                        '293.0.2.0.28', '293.0.2.0.20', '293.0.2.0.11', '293.0.2.0.6', '292.0.0.26.110',
                        '292.0.0.18.110', '292.0.0.16.110', '283.0.0.20.105', '274.0.0.21.90', '269.0.0.14.75',
                        '268.0.0.13.72', '268.0.0.9.72', '265.0.0.1.301', '259.0.0.16.104','313.0.0.0.263', '301.0.0.28.110', '301.0.0.27.110', '300.0.0.29.110', '294.0.4.0.15',
                        '293.0.2.0.28', '293.0.2.0.20', '293.0.2.0.11', '293.0.2.0.6', '292.0.0.26.110',
                        '292.0.0.18.110', '292.0.0.16.110', '283.0.0.20.105', '274.0.0.21.90', '269.0.0.14.75',
                        '268.0.0.13.72', '268.0.0.9.72', '265.0.0.1.301', '259.0.0.16.104'],

                        
                        }




        # Define a dictionary mapping manufacturer to model names along with DPI, resolution, and CPU
        device_info = {
            "Samsung": {
                "Galaxy S20": {"Version": 10, "dpi": "480dpi", "resolution": "1440x3200", "cpu": "exynos"},
                "Galaxy Note 20": {"Version": 10, "dpi": "480dpi", "resolution": "1440x3088", "cpu": "exynos"},
                "Galaxy S21": {"Version": 11, "dpi": "421dpi", "resolution": "1080x2400", "cpu": "exynos"},
                "Galaxy S10": {"Version": 9, "dpi": "550dpi", "resolution": "1440x3040", "cpu": "exynos"},
                "Galaxy S9": {"Version": 8, "dpi": "570dpi", "resolution": "1440x2960", "cpu": "exynos"},
                "Galaxy Note 10": {"Version": 9, "dpi": "401dpi", "resolution": "1080x2280", "cpu": "exynos"},
                "Galaxy Note 9": {"Version": 8, "dpi": "520dpi", "resolution": "1440x2960", "cpu": "exynos"},
                "Galaxy S21 Ultra": {"Version": 11, "dpi": "515dpi", "resolution": "1440x3200", "cpu": "exynos"},
                "Galaxy S21 Plus": {"Version": 11, "dpi": "394dpi", "resolution": "1080x2400", "cpu": "exynos"},
                "Galaxy S21 FE": {"Version": 11, "dpi": "393dpi", "resolution": "1080x2400", "cpu": "exynos"},
                "Galaxy Note 20 Lite": {"Version": 10, "dpi": "393dpi", "resolution": "1080x2400", "cpu": "exynos"},
                "Galaxy A72": {"Version": 11, "dpi": "407dpi", "resolution": "1080x2400", "cpu": "exynos"},
                "Galaxy A52": {"Version": 11, "dpi": "405dpi", "resolution": "1080x2400", "cpu": "exynos"},
                "Galaxy A32": {"Version": 11, "dpi": "270dpi", "resolution": "720x1600", "cpu": "exynos"},
                "Galaxy M62": {"Version": 11, "dpi": "407dpi", "resolution": "1080x2400", "cpu": "exynos"},
                "Galaxy M51": {"Version": 10, "dpi": "393dpi", "resolution": "1080x2340", "cpu": "exynos"},
                "Galaxy M42": {"Version": 11, "dpi": "270dpi", "resolution": "720x1600", "cpu": "exynos"},
                "Galaxy F62": {"Version": 11, "dpi": "393dpi", "resolution": "1080x2340", "cpu": "exynos"},
                "Galaxy F41": {"Version": 10, "dpi": "403dpi", "resolution": "1080x2340", "cpu": "exynos"},
                "Galaxy Z Fold 2": {"Version": 10, "dpi": "373dpi", "resolution": "1768x2208", "cpu": "exynos"},
                "Galaxy Z Flip 3": {"Version": 11, "dpi": "425dpi", "resolution": "1080x2640", "cpu": "exynos"},
                "Galaxy Fold": {"Version": 9, "dpi": "362dpi", "resolution": "1536x2152", "cpu": "exynos"},
                "Galaxy Tab S7 Plus": {"Version": 10, "dpi": "266dpi", "resolution": "1600x2560", "cpu": "exynos"},
                "Galaxy Tab S6 Lite": {"Version": 10, "dpi": "224dpi", "resolution": "1200x2000", "cpu": "exynos"},
                "Galaxy Tab A7": {"Version": 10, "dpi": "224dpi", "resolution": "1200x2000", "cpu": "exynos"},
                "Galaxy Tab Active 3": {"Version": 10, "dpi": "224dpi", "resolution": "1200x2000", "cpu": "exynos"},



            },
            # "Apple": {
            #     "iPhone 12": {"dpi": "458dpi", "resolution": "1170x2532", "cpu": "A14 Bionic", "Version": "14"},
            #     "iPhone 11": {"dpi": "326dpi", "resolution": "828x1792", "cpu": "A13 Bionic", "Version": "13"},
            #     "iPhone XS": {"dpi": "458dpi", "resolution": "1125x2436", "cpu": "A12 Bionic", "Version": "12"},
            #     "iPhone XR": {"dpi": "326dpi", "resolution": "828x1792", "cpu": "A12 Bionic", "Version": "12"},
            #     "iPhone SE": {"dpi": "326dpi", "resolution": "750x1334", "cpu": "A13 Bionic", "Version": "13"},
            #     "iPhone 8": {"dpi": "326dpi", "resolution": "750x1334", "cpu": "A11 Bionic", "Version": "11"},
            #     "iPhone 7": {"dpi": "326dpi", "resolution": "750x1334", "cpu": "A10 Fusion", "Version": "10"},
            #     "iPhone 12 Pro": {"dpi": "458dpi", "resolution": "1170x2532", "cpu": "A14 Bionic", "Version": "14"},
            #     "iPhone 11 Pro": {"dpi": "458dpi", "resolution": "1125x2436", "cpu": "A13 Bionic", "Version": "13"},
            #     "iPhone XS Max": {"dpi": "458dpi", "resolution": "1242x2688", "cpu": "A12 Bionic", "Version": "12"},
            #     "iPhone 8 Plus": {"dpi": "401dpi", "resolution": "1080x1920", "cpu": "A11 Bionic", "Version": "11"},
            #     "iPhone 7 Plus": {"dpi": "401dpi", "resolution": "1080x1920", "cpu": "A10 Fusion", "Version": "10"}
            # },

            "OnePlus": {
                "OnePlus 8T": {"Version": 10, "dpi": "402dpi", "resolution": "1080x2400", "cpu": "qcom"},
                "OnePlus 9": {"Version": 11, "dpi": "402dpi", "resolution": "1080x2400", "cpu": "qcom"},
                "OnePlus 7T": {"Version": 10, "dpi": "402dpi", "resolution": "1080x2400", "cpu": "qcom"},
                "OnePlus 6T": {"Version": 9, "dpi": "402dpi", "resolution": "1080x2280", "cpu": "qcom"},
                "OnePlus 5T": {"Version": 7, "dpi": "401dpi", "resolution": "1080x2160", "cpu": "qcom"},
                "OnePlus 8 Pro": {"Version": 10, "dpi": "513dpi", "resolution": "1440x3168", "cpu": "qcom"},
                "OnePlus 9 Pro": {"Version": 11, "dpi": "513dpi", "resolution": "1440x3216", "cpu": "qcom"},
                "OnePlus 7T Pro": {"Version": 10, "dpi": "513dpi", "resolution": "1440x3120", "cpu": "qcom"},
                "OnePlus 6T McLaren": {"Version": 9, "dpi": "402dpi", "resolution": "1080x2340", "cpu": "qcom"},
                "OnePlus 5T Star Wars": {"Version": 7, "dpi": "401dpi", "resolution": "1080x2160", "cpu": "qcom"}
            },

            "Google": {
                "Pixel 5": {"Version": 11, "dpi": "432dpi", "resolution": "1080x2340", "cpu": "qcom"},
                "Pixel 4": {"Version": 10, "dpi": "444dpi", "resolution": "1080x2280", "cpu": "qcom"},
                "Pixel 3": {"Version": 9, "dpi": "443dpi", "resolution": "1080x2160", "cpu": "qcom"},
                "Pixel 2": {"Version": 8, "dpi": "441dpi", "resolution": "1080x1920", "cpu": "qcom"},
                "Pixel": {"Version": 7, "dpi": "441dpi", "resolution": "1080x1920", "cpu": "qcom"},
                "Pixel 5 Pro": {"Version": 11, "dpi": "432dpi", "resolution": "1440x3120", "cpu": "qcom"},
                "Pixel 5 Max": {"Version": 11, "dpi": "432dpi", "resolution": "1440x3120", "cpu": "qcom"},
                "Pixel 4 XL": {"Version": 10, "dpi": "537dpi", "resolution": "1440x3040", "cpu": "qcom"},
                "Pixel 4 Pro": {"Version": 10, "dpi": "537dpi", "resolution": "1440x3040", "cpu": "qcom"},
                "Pixel 4 Max": {"Version": 10, "dpi": "537dpi", "resolution": "1440x3040", "cpu": "qcom"},
                "Pixel 3 XL": {"Version": 9, "dpi": "523dpi", "resolution": "1440x2960", "cpu": "qcom"},
                "Pixel 3 Pro": {"Version": 9, "dpi": "523dpi", "resolution": "1440x2960", "cpu": "qcom"},
                "Pixel 3 Max": {"Version": 9, "dpi": "523dpi", "resolution": "1440x2960", "cpu": "qcom"},
                "Pixel 2 XL": {"Version": 8, "dpi": "537dpi", "resolution": "1440x2880", "cpu": "qcom"},
                "Pixel 2 Pro": {"Version": 8, "dpi": "537dpi", "resolution": "1440x2880", "cpu": "qcom"},
                "Pixel 2 Max": {"Version": 8, "dpi": "537dpi", "resolution": "1440x2880", "cpu": "qcom"},
                "Pixel XL": {"Version": 7, "dpi": "534dpi", "resolution": "1440x2560", "cpu": "qcom"},
                "Pixel Pro": {"Version": 7, "dpi": "534dpi", "resolution": "1440x2560", "cpu": "qcom"},
                "Pixel Max": {"Version": 7, "dpi": "534dpi", "resolution": "1440x2560", "cpu": "qcom"}
            },

            "Sony": {
                "Xperia 1 III": {"Version": 11, "dpi": "643dpi", "resolution": "1644x3840", "cpu": "qcom"},
                "Xperia 1 III Pro": {"Version": 11, "dpi": "643dpi", "resolution": "1644x3840", "cpu": "qcom"},
                "Xperia 1 III Max": {"Version": 11, "dpi": "643dpi", "resolution": "1644x3840", "cpu": "qcom"},
                "Xperia 1 III Mini": {"Version": 11, "dpi": "643dpi", "resolution": "1644x3840", "cpu": "qcom"},
                "Xperia 5 III": {"Version": 11, "dpi": "643dpi", "resolution": "1080x2520", "cpu": "qcom"},
                "Xperia 5 III Pro": {"Version": 11, "dpi": "643dpi", "resolution": "1080x2520", "cpu": "qcom"},
                "Xperia 5 III Max": {"Version": 11, "dpi": "643dpi", "resolution": "1080x2520", "cpu": "qcom"},
                "Xperia 5 III Mini": {"Version": 11, "dpi": "643dpi", "resolution": "1080x2520", "cpu": "qcom"},
                "Xperia 1 II": {"Version": 10, "dpi": "643dpi", "resolution": "1644x3840", "cpu": "qcom"},
                "Xperia 1 II Pro": {"Version": 10, "dpi": "643dpi", "resolution": "1644x3840", "cpu": "qcom"},
                "Xperia 1 II Max": {"Version": 10, "dpi": "643dpi", "resolution": "1644x3840", "cpu": "qcom"},
                "Xperia 1 II Mini": {"Version": 10, "dpi": "643dpi", "resolution": "1644x3840", "cpu": "qcom"},
                "Xperia 10 III": {"Version": 11, "dpi": "457dpi", "resolution": "1080x2520", "cpu": "qcom"},
                "Xperia 10 III Pro": {"Version": 11, "dpi": "457dpi", "resolution": "1080x2520", "cpu": "qcom"},
                "Xperia 10 III Max": {"Version": 11, "dpi": "457dpi", "resolution": "1080x2520", "cpu": "qcom"},
                "Xperia 10 III Mini": {"Version": 11, "dpi": "457dpi", "resolution": "1080x2520", "cpu": "qcom"},
                "Xperia 10 II": {"Version": 10, "dpi": "457dpi", "resolution": "1080x2520", "cpu": "qcom"},
                "Xperia 10 II Pro": {"Version": 10, "dpi": "457dpi", "resolution": "1080x2520", "cpu": "qcom"},
                "Xperia 10 II Max": {"Version": 10, "dpi": "457dpi", "resolution": "1080x2520", "cpu": "qcom"},
                "Xperia 10 II Mini": {"Version": 10, "dpi": "457dpi", "resolution": "1080x2520", "cpu": "qcom"}
        },
            "Huawei": {
                "Mate 40 Pro": {"Version": 10, "dpi": "441dpi", "resolution": "1344x2772", "cpu": "kirin"},
                "Mate 40 Pro Max": {"Version": 10, "dpi": "441dpi", "resolution": "1344x2772", "cpu": "kirin"},
                "Mate 40 Pro Mini": {"Version": 10, "dpi": "441dpi", "resolution": "1344x2772", "cpu": "kirin"},
                "Mate 30 Pro": {"Version": 10, "dpi": "409dpi", "resolution": "1176x2400", "cpu": "kirin"},
                "Mate 30 Pro Max": {"Version": 10, "dpi": "409dpi", "resolution": "1176x2400", "cpu": "kirin"},
                "Mate 30 Pro Mini": {"Version": 10, "dpi": "409dpi", "resolution": "1176x2400", "cpu": "kirin"},
                "Mate 20 Pro": {"Version": 9, "dpi": "538dpi", "resolution": "1440x3120", "cpu": "kirin"},
                "Mate 20 Pro Max": {"Version": 9, "dpi": "538dpi", "resolution": "1440x3120", "cpu": "kirin"},
                "Mate 20 Pro Mini": {"Version": 9, "dpi": "538dpi", "resolution": "1440x3120", "cpu": "kirin"},
                "P40 Pro": {"Version": 10, "dpi": "441dpi", "resolution": "1200x2640", "cpu": "kirin"},
                "P40 Pro Max": {"Version": 10, "dpi": "441dpi", "resolution": "1200x2640", "cpu": "kirin"},
                "P40 Pro Mini": {"Version": 10, "dpi": "441dpi", "resolution": "1200x2640", "cpu": "kirin"},
                "P30 Pro": {"Version": 9, "dpi": "398dpi", "resolution": "1080x2340", "cpu": "kirin"},
                "P30 Pro Max": {"Version": 9, "dpi": "398dpi", "resolution": "1080x2340", "cpu": "kirin"},
                "P30 Pro Mini": {"Version": 9, "dpi": "398dpi", "resolution": "1080x2340", "cpu": "kirin"},
                "Mate X2": {"Version": 11, "dpi": "413dpi", "resolution": "2200x2480", "cpu": "kirin"},
                "Mate 40": {"Version": 10, "dpi": "441dpi", "resolution": "1080x2340", "cpu": "kirin"},
                "Mate 30": {"Version": 10, "dpi": "409dpi", "resolution": "1080x2340", "cpu": "kirin"},
                "Mate 20": {"Version": 9, "dpi": "538dpi", "resolution": "1080x2244", "cpu": "kirin"},
                "P40": {"Version": 10, "dpi": "441dpi", "resolution": "1080x2340", "cpu": "kirin"},
                "P30": {"Version": 9, "dpi": "398dpi", "resolution": "1080x2340", "cpu": "kirin"},
                "P20": {"Version": 8, "dpi": "429dpi", "resolution": "1080x2244", "cpu": "kirin"},
                "Nova 8": {"Version": 11, "dpi": "443dpi", "resolution": "1080x2400", "cpu": "kirin"},
                "Nova 7": {"Version": 10, "dpi": "405dpi", "resolution": "1080x2400", "cpu": "kirin"},
                "Honor V40": {"Version": 11, "dpi": "441dpi", "resolution": "1236x2676", "cpu": "kirin"},
                "Honor 30": {"Version": 10, "dpi": "400dpi", "resolution": "1080x2400", "cpu": "kirin"},
                "Honor 20": {"Version": 9, "dpi": "412dpi", "resolution": "1080x2340", "cpu": "kirin"},
                "Enjoy 20": {"Version": 10, "dpi": "269dpi", "resolution": "720x1600", "cpu": "kirin"},
                "Y9a": {"Version": 10, "dpi": "415dpi", "resolution": "1080x2400", "cpu": "kirin"},
                "Y7a": {"Version": 10, "dpi": "269dpi", "resolution": "720x1600", "cpu": "kirin"}


            },

        "Xiaomi": {
                "Mi 11 Pro": {"Version": 11, "dpi": "515dpi", "resolution": "1440x3200", "cpu": "qcom"},
                "Mi 11 Ultra": {"Version": 11, "dpi": "515dpi", "resolution": "1440x3200", "cpu": "qcom"},
                "Mi 11 Lite": {"Version": 11, "dpi": "402dpi", "resolution": "1080x2400", "cpu": "qcom"},
                "Mi 10 Pro": {"Version": 10, "dpi": "386dpi", "resolution": "1080x2340", "cpu": "qcom"},
                "Mi 10 Ultra": {"Version": 10, "dpi": "386dpi", "resolution": "1080x2340", "cpu": "qcom"},
                "Mi 10 Lite": {"Version": 10, "dpi": "409dpi", "resolution": "1080x2400", "cpu": "qcom"},
                "Mi 9 Pro": {"Version": 9, "dpi": "403dpi", "resolution": "1080x2340", "cpu": "qcom"},
                "Mi 9T Pro": {"Version": 9, "dpi": "403dpi", "resolution": "1080x2340", "cpu": "qcom"},
                "Mi 9 SE": {"Version": 9, "dpi": "432dpi", "resolution": "1080x2340", "cpu": "qcom"},
                "Mi 8 Pro": {"Version": 8, "dpi": "403dpi", "resolution": "1080x2248", "cpu": "qcom"},
                "Mi 8 Max": {"Version": 8, "dpi": "403dpi", "resolution": "1080x2248", "cpu": "qcom"},
                "Mi 8 Mini": {"Version": 8, "dpi": "403dpi", "resolution": "1080x2248", "cpu": "qcom"},
                "Mi Mix Pro": {"Version": 7, "dpi": "362dpi", "resolution": "1080x2340", "cpu": "qcom"},
                "Mi Mix Max": {"Version": 7, "dpi": "362dpi", "resolution": "1080x2340", "cpu": "qcom"},
                "Mi Mix Mini": {"Version": 7, "dpi": "362dpi", "resolution": "1080x2340", "cpu": "qcom"},
                "Mi Note 10 Pro": {"Version": 10, "dpi": "398dpi", "resolution": "1080x2340", "cpu": "qcom"},
                "Mi Note 10 Max": {"Version": 10, "dpi": "398dpi", "resolution": "1080x2340", "cpu": "qcom"},
                "Mi Note 10 Mini": {"Version": 10, "dpi": "398dpi", "resolution": "1080x2340", "cpu": "qcom"},
                "Redmi Note 9 Pro": {"Version": 10, "dpi": "395dpi", "resolution": "1080x2340", "cpu": "qcom"},
                "Redmi Note 9 Max": {"Version": 10, "dpi": "395dpi", "resolution": "1080x2340", "cpu": "qcom"},
                "Redmi Note 9 Mini": {"Version": 10, "dpi": "395dpi", "resolution": "1080x2340", "cpu": "qcom"},
                "Redmi 10 Pro": {"Version": 11, "dpi": "402dpi", "resolution": "1080x2400", "cpu": "qcom"},
                "Redmi 10 Max": {"Version": 11, "dpi": "402dpi", "resolution": "1080x2400", "cpu": "qcom"},
                "Redmi 10 Mini": {"Version": 11, "dpi": "402dpi", "resolution": "1080x2400", "cpu": "qcom"},
                "POCO F3 Pro": {"Version": 11, "dpi": "395dpi", "resolution": "1080x2400", "cpu": "qcom"}
            },

            "ASUS": {
                "ZenFone 7": {"Version": 10, "dpi": "386dpi", "resolution": "1080x2400", "cpu": "qcom"},
                "ZenFone 7 Pro": {"Version": 10, "dpi": "386dpi", "resolution": "1080x2400", "cpu": "qcom"},
                "ZenFone 7 Max": {"Version": 10, "dpi": "386dpi", "resolution": "1080x2400", "cpu": "qcom"},
                "ZenFone 7 Mini": {"Version": 10, "dpi": "386dpi", "resolution": "1080x2400", "cpu": "qcom"},
                "ZenFone 6": {"Version": 9, "dpi": "403dpi", "resolution": "1080x2340", "cpu": "qcom"},
                "ZenFone 6 Pro": {"Version": 9, "dpi": "403dpi", "resolution": "1080x2340", "cpu": "qcom"},
                "ZenFone 6 Max": {"Version": 9, "dpi": "403dpi", "resolution": "1080x2340", "cpu": "qcom"},
                "ZenFone 6 Mini": {"Version": 9, "dpi": "403dpi", "resolution": "1080x2340", "cpu": "qcom"},
                "ZenFone 5": {"Version": 8, "dpi": "403dpi", "resolution": "1080x2248", "cpu": "qcom"},
                "ZenFone 5 Pro": {"Version": 8, "dpi": "403dpi", "resolution": "1080x2248", "cpu": "qcom"},
                "ZenFone 5 Max": {"Version": 8, "dpi": "403dpi", "resolution": "1080x2248", "cpu": "qcom"},
                "ZenFone 5 Mini": {"Version": 8, "dpi": "403dpi", "resolution": "1080x2248", "cpu": "qcom"},
                "ZenFone 4": {"Version": 7, "dpi": "401dpi", "resolution": "1080x2246", "cpu": "qcom"},
                "ZenFone 4 Pro": {"Version": 7, "dpi": "401dpi", "resolution": "1080x2246", "cpu": "qcom"},
                "ZenFone 4 Max": {"Version": 7, "dpi": "401dpi", "resolution": "1080x2246", "cpu": "qcom"},
                "ZenFone 4 Mini": {"Version": 7, "dpi": "401dpi", "resolution": "1080x2246", "cpu": "qcom"},
                "ZenFone 8": {"Version": 11, "dpi": "400dpi", "resolution": "1080x2400", "cpu": "qcom"},
                "ZenFone 8 Pro": {"Version": 11, "dpi": "400dpi", "resolution": "1080x2400", "cpu": "qcom"},
                "ZenFone 8 Max": {"Version": 11, "dpi": "400dpi", "resolution": "1080x2400", "cpu": "qcom"},
                "ZenFone 8 Mini": {"Version": 11, "dpi": "400dpi", "resolution": "1080x2400", "cpu": "qcom"},
                "ROG Phone 5": {"Version": 11, "dpi": "391dpi", "resolution": "1080x2448", "cpu": "qcom"},
                "ROG Phone 5 Pro": {"Version": 11, "dpi": "391dpi", "resolution": "1080x2448", "cpu": "qcom"},
                "ROG Phone 5 Ultimate": {"Version": 11, "dpi": "391dpi", "resolution": "1080x2448", "cpu": "qcom"},
                "ZenFone 7 Deluxe": {"Version": 10, "dpi": "386dpi", "resolution": "1080x2400", "cpu": "qcom"},
                "ZenFone 7 Ultra": {"Version": 10, "dpi": "386dpi", "resolution": "1080x2400", "cpu": "qcom"},
                "ROG Phone 3": {"Version": 10, "dpi": "391dpi", "resolution": "1080x2340", "cpu": "qcom"},
                "ROG Phone 3 Pro": {"Version": 10, "dpi": "391dpi", "resolution": "1080x2340", "cpu": "qcom"},
                "ROG Phone 3 Ultimate": {"Version": 10, "dpi": "391dpi", "resolution": "1080x2340", "cpu": "qcom"},
                "ZenFone 6S": {"Version": 9, "dpi": "403dpi", "resolution": "1080x2340", "cpu": "qcom"},
                "ZenFone 6S Pro": {"Version": 9, "dpi": "403dpi", "resolution": "1080x2340", "cpu": "qcom"},
                "ZenFone 6S Max": {"Version": 9, "dpi": "403dpi", "resolution": "1080x2340", "cpu": "qcom"},
                "ZenFone 6S Mini": {"Version": 9, "dpi": "403dpi", "resolution": "1080x2340", "cpu": "qcom"}
            },


            "LG": {
                "LG Velvet": {"Version": 10, "dpi": "395dpi", "resolution": "1080x2460", "cpu": "qcom"},
                "LG Velvet Pro": {"Version": 10, "dpi": "395dpi", "resolution": "1080x2460", "cpu": "qcom"},
                "LG Velvet Max": {"Version": 10, "dpi": "395dpi", "resolution": "1080x2460", "cpu": "qcom"},
                "LG Velvet Mini": {"Version": 10, "dpi": "395dpi", "resolution": "1080x2460", "cpu": "qcom"},
                "LG G8": {"Version": 9, "dpi": "564dpi", "resolution": "1440x3120", "cpu": "qcom"},
                "LG G8 Pro": {"Version": 9, "dpi": "564dpi", "resolution": "1440x3120", "cpu": "qcom"},
                "LG G8 Max": {"Version": 9, "dpi": "564dpi", "resolution": "1440x3120", "cpu": "qcom"},
                "LG G8 Mini": {"Version": 9, "dpi": "564dpi", "resolution": "1440x3120", "cpu": "qcom"},
                "LG G7": {"Version": 8, "dpi": "563dpi", "resolution": "1440x3120", "cpu": "qcom"},
                "LG G7 Pro": {"Version": 8, "dpi": "563dpi", "resolution": "1440x3120", "cpu": "qcom"},
                "LG G7 Max": {"Version": 8, "dpi": "563dpi", "resolution": "1440x3120", "cpu": "qcom"},
                "LG G7 Mini": {"Version": 8, "dpi": "563dpi", "resolution": "1440x3120", "cpu": "qcom"},
                "LG G6": {"Version": 7, "dpi": "564dpi", "resolution": "1440x2880", "cpu": "qcom"},
                "LG G6 Pro": {"Version": 7, "dpi": "564dpi", "resolution": "1440x2880", "cpu": "qcom"},
                "LG G6 Max": {"Version": 7, "dpi": "564dpi", "resolution": "1440x2880", "cpu": "qcom"},
                "LG G6 Mini": {"Version": 7, "dpi": "564dpi", "resolution": "1440x2880", "cpu": "qcom"},
                "LG V60 ThinQ": {"Version": 10, "dpi": "395dpi", "resolution": "1080x2460", "cpu": "qcom"},
                "LG V60 ThinQ Pro": {"Version": 10, "dpi": "395dpi", "resolution": "1080x2460", "cpu": "qcom"},
                "LG V60 ThinQ Max": {"Version": 10, "dpi": "395dpi", "resolution": "1080x2460", "cpu": "qcom"},
                "LG V60 ThinQ Mini": {"Version": 10, "dpi": "395dpi", "resolution": "1080x2460", "cpu": "qcom"},
                "LG V50 ThinQ": {"Version": 9, "dpi": "564dpi", "resolution": "1440x3120", "cpu": "qcom"},
                "LG V50 ThinQ Pro": {"Version": 9, "dpi": "564dpi", "resolution": "1440x3120", "cpu": "qcom"},
                "LG V50 ThinQ Max": {"Version": 9, "dpi": "564dpi", "resolution": "1440x3120", "cpu": "qcom"},
                "LG V50 ThinQ Mini": {"Version": 9, "dpi": "564dpi", "resolution": "1440x3120", "cpu": "qcom"},
                "LG G5": {"Version": 7, "dpi": "564dpi", "resolution": "1440x2880", "cpu": "qcom"},
                "LG G5 Pro": {"Version": 7, "dpi": "564dpi", "resolution": "1440x2880", "cpu": "qcom"},
                "LG G5 Max": {"Version": 7, "dpi": "564dpi", "resolution": "1440x2880", "cpu": "qcom"},
                "LG G5 Mini": {"Version": 7, "dpi": "564dpi", "resolution": "1440x2880", "cpu": "qcom"}

            }

        }
        #-------------------------------------------ADD APPLE-------
        # Select a manufacturer
        manufacturer = fake.random_element(elements=("Samsung", "OnePlus", "Google", "Sony", "Huawei", "Xiaomi", "ASUS", "LG"))

        # Select a model based on the manufacturer
        model_info = device_info[manufacturer]
        model = fake.random_element(elements=list(model_info.keys()))

        # Get the DPI, resolution, and CPU for the selected model
        version = model_info[model]["Version"]
        android_release = android_releases[version]


        selected_app_version = random.choice(app_versions[android_release])

        # selected_app_version = random.choice(app_versions[version])
        dpi = model_info[model]["dpi"]
        resolution = model_info[model]["resolution"]
        cpu = model_info[model]["cpu"]

        # Generate other fake device information
        device_name = fake.user_name()

        version_code = fake.numerify(text="#########")

        device = {
                    "app_version": selected_app_version,
                    "android_version": version,
                    "android_release": android_release,
                    "dpi": dpi,
                    "resolution": resolution,
                    "manufacturer": manufacturer,
                    "device": device_name+fake.user_name(),
                    "model": model,
                    "cpu": cpu,
                    "version_code": version_code,
                }
        
        

        return device


