from manim import *
from math import *
import os

config.frame_size = (1280, 720)
config.frame_width = 10.0
config.frame_rate = 10


# ---- Early Exit (Preview Mode) ----
import os as _os
from manim.scene.scene import Scene as _Scene
_PREVIEW_LIMIT_ACTIONS = int(_os.environ.get("PREVIEW_LIMIT_ACTIONS", "8"))
_play_action_counter = 0
_exit_preview_now = False

_original_play = _Scene.play
_original_wait = _Scene.wait
_original_add = _Scene.add
_original_add_fg = _Scene.add_foreground_mobject

def _preview_play(self, *args, **kwargs):
    global _play_action_counter, _exit_preview_now
    if _exit_preview_now:
        return  # skip further animations
    _play_action_counter += 1
    if _play_action_counter >= _PREVIEW_LIMIT_ACTIONS:
        _exit_preview_now = True
        # Execute this final animation once, then future ones skipped
        return _original_play(self, *args, **kwargs)
    return _original_play(self, *args, **kwargs)

def _preview_wait(self, duration=0.0):
    if _exit_preview_now:
        return  # skip waits entirely
    return _original_wait(self, duration)

def _preview_add(self, *mobs):
    if _exit_preview_now:
        # Allow minimal additions to keep scene valid; or skip entirely
        return
    return _original_add(self, *mobs)

def _preview_add_fg(self, *mobs):
    if _exit_preview_now:
        return
    return _original_add_fg(self, *mobs)

_Scene.play = _preview_play
_Scene.wait = _preview_wait
_Scene.add = _preview_add
_Scene.add_foreground_mobject = _preview_add_fg


from manim import *
import math

# =============================================================================
# DISTRIBUTION ANIMATION - Story-Driven Architecture
# =============================================================================
# Generated using the primitives system for modular, narrative animations
# Theme: youtube_dark
# Narrative Style: explainer
# =============================================================================

# --- Data ---
TIMES = ['1800', '1801', '1802', '1803', '1804', '1805', '1806', '1807', '1808', '1809', '1810', '1811', '1812', '1813', '1814', '1815', '1816', '1817', '1818', '1819', '1820', '1821', '1822', '1823', '1824', '1825', '1826', '1827', '1828', '1829', '1830', '1831', '1832', '1833', '1834', '1835', '1836', '1837', '1838', '1839', '1840', '1841', '1842', '1843', '1844', '1845', '1846', '1847', '1848', '1849', '1850', '1851', '1852', '1853', '1854', '1855', '1856', '1857', '1858', '1859', '1860', '1861', '1862', '1863', '1864', '1865', '1866', '1867', '1868', '1869', '1870', '1871', '1872', '1873', '1874', '1875', '1876', '1877', '1878', '1879', '1880', '1881', '1882', '1883', '1884', '1885', '1886', '1887', '1888', '1889', '1890', '1891', '1892', '1893', '1894', '1895', '1896', '1897', '1898', '1899', '1900', '1901', '1902', '1903', '1904', '1905', '1906', '1907', '1908', '1909', '1910', '1911', '1912', '1913', '1914', '1915', '1916', '1917', '1918', '1919', '1920', '1921', '1922', '1923', '1924', '1925', '1926', '1927', '1928', '1929', '1930', '1931', '1932', '1933', '1934', '1935', '1936', '1937', '1938', '1939', '1940', '1941', '1942', '1943', '1944', '1945', '1946', '1947', '1948', '1949', '1950', '1951', '1952', '1953', '1954', '1955', '1956', '1957', '1958', '1959', '1960', '1961', '1962', '1963', '1964', '1965', '1966', '1967', '1968', '1969', '1970', '1971', '1972', '1973', '1974', '1975', '1976', '1977', '1978', '1979', '1980', '1981', '1982', '1983', '1984', '1985', '1986', '1987', '1988', '1989', '1990', '1991', '1992', '1993', '1994', '1995', '1996', '1997', '1998', '1999', '2000', '2001', '2002', '2003', '2004', '2005', '2006', '2007', '2008', '2009', '2010', '2011', '2012', '2013', '2014', '2015', '2016', '2017', '2018']
BIN_LABELS = ['1-9', '9-18', '18-26', '26-34', '34-43', '43-51', '51-59', '59-68', '68-76', '76-84']
HISTOGRAMS = {'1800': [0, 0, 19, 125, 39, 1, 0, 0, 0, 0], '1801': [0, 0, 20, 123, 41, 0, 0, 0, 0, 0], '1802': [0, 0, 20, 123, 40, 1, 0, 0, 0, 0], '1803': [0, 0, 20, 125, 38, 1, 0, 0, 0, 0], '1804': [0, 0, 20, 124, 39, 1, 0, 0, 0, 0], '1805': [0, 0, 19, 125, 38, 2, 0, 0, 0, 0], '1806': [0, 0, 19, 124, 37, 4, 0, 0, 0, 0], '1807': [0, 0, 19, 124, 39, 2, 0, 0, 0, 0], '1808': [0, 1, 19, 124, 39, 1, 0, 0, 0, 0], '1809': [0, 1, 19, 125, 39, 0, 0, 0, 0, 0], '1810': [0, 0, 19, 124, 40, 1, 0, 0, 0, 0], '1811': [0, 0, 19, 124, 41, 0, 0, 0, 0, 0], '1812': [0, 0, 19, 125, 39, 1, 0, 0, 0, 0], '1813': [0, 0, 19, 127, 37, 1, 0, 0, 0, 0], '1814': [0, 0, 19, 124, 41, 0, 0, 0, 0, 0], '1815': [0, 0, 19, 122, 40, 3, 0, 0, 0, 0], '1816': [0, 0, 19, 123, 40, 2, 0, 0, 0, 0], '1817': [0, 0, 19, 122, 40, 3, 0, 0, 0, 0], '1818': [1, 0, 19, 121, 40, 3, 0, 0, 0, 0], '1819': [1, 0, 19, 121, 41, 2, 0, 0, 0, 0], '1820': [1, 0, 19, 121, 40, 3, 0, 0, 0, 0], '1821': [0, 0, 19, 123, 41, 1, 0, 0, 0, 0], '1822': [0, 0, 19, 122, 39, 4, 0, 0, 0, 0], '1823': [0, 0, 19, 122, 39, 4, 0, 0, 0, 0], '1824': [0, 0, 19, 122, 40, 3, 0, 0, 0, 0], '1825': [0, 0, 19, 123, 39, 3, 0, 0, 0, 0], '1826': [0, 0, 20, 122, 40, 2, 0, 0, 0, 0], '1827': [0, 0, 20, 122, 40, 2, 0, 0, 0, 0], '1828': [0, 0, 19, 123, 41, 1, 0, 0, 0, 0], '1829': [0, 0, 19, 123, 41, 1, 0, 0, 0, 0], '1830': [0, 0, 19, 123, 40, 2, 0, 0, 0, 0], '1831': [0, 0, 19, 123, 41, 1, 0, 0, 0, 0], '1832': [0, 0, 19, 124, 40, 1, 0, 0, 0, 0], '1833': [0, 0, 20, 121, 42, 1, 0, 0, 0, 0], '1834': [0, 0, 20, 122, 42, 0, 0, 0, 0, 0], '1835': [0, 0, 19, 122, 41, 2, 0, 0, 0, 0], '1836': [0, 0, 19, 124, 39, 2, 0, 0, 0, 0], '1837': [0, 0, 19, 123, 41, 1, 0, 0, 0, 0], '1838': [0, 0, 19, 123, 40, 2, 0, 0, 0, 0], '1839': [0, 0, 20, 122, 40, 2, 0, 0, 0, 0], '1840': [0, 0, 19, 122, 41, 2, 0, 0, 0, 0], '1841': [0, 0, 20, 119, 42, 3, 0, 0, 0, 0], '1842': [0, 0, 20, 119, 43, 2, 0, 0, 0, 0], '1843': [0, 0, 20, 120, 41, 3, 0, 0, 0, 0], '1844': [0, 1, 19, 119, 41, 4, 0, 0, 0, 0], '1845': [0, 0, 20, 119, 40, 5, 0, 0, 0, 0], '1846': [0, 0, 21, 120, 42, 1, 0, 0, 0, 0], '1847': [0, 0, 20, 121, 42, 1, 0, 0, 0, 0], '1848': [0, 1, 20, 118, 43, 2, 0, 0, 0, 0], '1849': [0, 2, 20, 118, 42, 2, 0, 0, 0, 0], '1850': [0, 2, 19, 120, 38, 5, 0, 0, 0, 0], '1851': [0, 0, 20, 119, 42, 3, 0, 0, 0, 0], '1852': [0, 0, 19, 120, 43, 2, 0, 0, 0, 0], '1853': [0, 0, 19, 121, 42, 2, 0, 0, 0, 0], '1854': [1, 0, 19, 119, 41, 3, 1, 0, 0, 0], '1855': [0, 0, 19, 121, 41, 3, 0, 0, 0, 0], '1856': [0, 1, 19, 120, 41, 3, 0, 0, 0, 0], '1857': [0, 0, 19, 120, 44, 1, 0, 0, 0, 0], '1858': [0, 0, 19, 120, 44, 0, 1, 0, 0, 0], '1859': [0, 0, 19, 122, 40, 3, 0, 0, 0, 0], '1860': [0, 0, 20, 120, 38, 6, 0, 0, 0, 0], '1861': [0, 0, 19, 121, 41, 3, 0, 0, 0, 0], '1862': [0, 0, 20, 121, 39, 4, 0, 0, 0, 0], '1863': [0, 0, 19, 123, 39, 3, 0, 0, 0, 0], '1864': [0, 0, 20, 120, 42, 2, 0, 0, 0, 0], '1865': [0, 0, 22, 119, 41, 2, 0, 0, 0, 0], '1866': [0, 0, 22, 122, 37, 3, 0, 0, 0, 0], '1867': [1, 0, 23, 116, 39, 5, 0, 0, 0, 0], '1868': [1, 3, 21, 115, 40, 4, 0, 0, 0, 0], '1869': [0, 1, 21, 118, 41, 3, 0, 0, 0, 0], '1870': [0, 0, 22, 116, 42, 4, 0, 0, 0, 0], '1871': [0, 0, 21, 117, 41, 5, 0, 0, 0, 0], '1872': [0, 0, 23, 114, 40, 7, 0, 0, 0, 0], '1873': [0, 0, 21, 116, 41, 6, 0, 0, 0, 0], '1874': [0, 0, 21, 116, 41, 6, 0, 0, 0, 0], '1875': [1, 0, 21, 114, 43, 5, 0, 0, 0, 0], '1876': [0, 0, 21, 115, 40, 8, 0, 0, 0, 0], '1877': [0, 0, 20, 116, 39, 9, 0, 0, 0, 0], '1878': [0, 0, 21, 113, 42, 7, 1, 0, 0, 0], '1879': [0, 0, 20, 116, 39, 8, 1, 0, 0, 0], '1880': [0, 0, 20, 116, 41, 6, 1, 0, 0, 0], '1881': [0, 0, 18, 118, 39, 9, 0, 0, 0, 0], '1882': [0, 0, 18, 116, 40, 10, 0, 0, 0, 0], '1883': [0, 0, 17, 115, 42, 10, 0, 0, 0, 0], '1884': [0, 0, 16, 114, 45, 9, 0, 0, 0, 0], '1885': [0, 0, 14, 116, 43, 10, 1, 0, 0, 0], '1886': [0, 0, 14, 116, 42, 11, 1, 0, 0, 0], '1887': [0, 0, 13, 117, 40, 12, 2, 0, 0, 0], '1888': [0, 1, 13, 116, 39, 14, 1, 0, 0, 0], '1889': [1, 0, 13, 115, 39, 14, 2, 0, 0, 0], '1890': [2, 0, 13, 113, 41, 15, 0, 0, 0, 0], '1891': [1, 0, 15, 111, 41, 15, 1, 0, 0, 0], '1892': [0, 1, 16, 112, 38, 16, 1, 0, 0, 0], '1893': [1, 0, 16, 112, 36, 16, 3, 0, 0, 0], '1894': [0, 0, 15, 114, 36, 18, 1, 0, 0, 0], '1895': [0, 0, 15, 114, 36, 16, 3, 0, 0, 0], '1896': [0, 0, 13, 116, 35, 16, 4, 0, 0, 0], '1897': [0, 0, 12, 115, 36, 18, 3, 0, 0, 0], '1898': [0, 0, 13, 114, 37, 17, 3, 0, 0, 0], '1899': [0, 0, 16, 108, 39, 20, 1, 0, 0, 0], '1900': [0, 0, 15, 108, 42, 16, 3, 0, 0, 0], '1901': [0, 0, 15, 108, 40, 17, 4, 0, 0, 0], '1902': [0, 1, 13, 108, 39, 19, 4, 0, 0, 0], '1903': [0, 0, 15, 107, 37, 20, 5, 0, 0, 0], '1904': [1, 0, 13, 106, 39, 20, 5, 0, 0, 0], '1905': [0, 1, 13, 105, 40, 19, 6, 0, 0, 0], '1906': [0, 0, 15, 104, 39, 19, 7, 0, 0, 0], '1907': [0, 0, 14, 105, 38, 17, 10, 0, 0, 0], '1908': [0, 0, 15, 103, 38, 17, 11, 0, 0, 0], '1909': [0, 0, 13, 105, 38, 16, 12, 0, 0, 0], '1910': [0, 0, 12, 105, 37, 16, 14, 0, 0, 0], '1911': [0, 0, 12, 102, 39, 19, 12, 0, 0, 0], '1912': [0, 0, 12, 100, 40, 18, 14, 0, 0, 0], '1913': [0, 0, 11, 105, 37, 17, 14, 0, 0, 0], '1914': [0, 0, 12, 106, 37, 17, 12, 0, 0, 0], '1915': [1, 1, 10, 104, 43, 13, 12, 0, 0, 0], '1916': [0, 0, 12, 105, 41, 15, 11, 0, 0, 0], '1917': [0, 0, 16, 103, 39, 15, 11, 0, 0, 0], '1918': [9, 56, 52, 44, 10, 10, 3, 0, 0, 0], '1919': [0, 1, 17, 97, 42, 15, 11, 1, 0, 0], '1920': [0, 3, 13, 98, 39, 14, 16, 1, 0, 0], '1921': [0, 1, 16, 96, 39, 12, 15, 5, 0, 0], '1922': [0, 1, 14, 92, 43, 12, 17, 5, 0, 0], '1923': [0, 0, 8, 97, 44, 11, 17, 7, 0, 0], '1924': [0, 0, 7, 91, 50, 12, 18, 6, 0, 0], '1925': [0, 0, 8, 88, 53, 10, 18, 7, 0, 0], '1926': [0, 0, 9, 81, 57, 12, 17, 8, 0, 0], '1927': [0, 0, 10, 78, 57, 14, 17, 8, 0, 0], '1928': [0, 0, 8, 77, 58, 15, 17, 9, 0, 0], '1929': [0, 0, 8, 77, 56, 16, 19, 8, 0, 0], '1930': [0, 0, 6, 74, 60, 17, 16, 11, 0, 0], '1931': [0, 1, 8, 74, 52, 22, 15, 12, 0, 0], '1932': [1, 0, 10, 70, 51, 23, 17, 12, 0, 0], '1933': [2, 4, 8, 64, 53, 23, 18, 12, 0, 0], '1934': [0, 0, 4, 64, 61, 24, 17, 14, 0, 0], '1935': [0, 0, 1, 62, 62, 27, 18, 14, 0, 0], '1936': [0, 0, 2, 60, 59, 31, 18, 14, 0, 0], '1937': [0, 0, 1, 58, 59, 34, 16, 16, 0, 0], '1938': [0, 0, 1, 52, 60, 37, 18, 16, 0, 0], '1939': [0, 0, 1, 50, 59, 38, 19, 16, 1, 0], '1940': [0, 0, 1, 50, 59, 37, 23, 14, 0, 0], '1941': [0, 1, 4, 59, 59, 30, 18, 13, 0, 0], '1942': [0, 1, 10, 55, 56, 25, 24, 12, 1, 0], '1943': [0, 2, 13, 48, 58, 30, 18, 14, 1, 0], '1944': [0, 2, 9, 58, 56, 27, 18, 12, 2, 0], '1945': [0, 2, 2, 46, 62, 34, 24, 9, 5, 0], '1946': [0, 0, 2, 26, 58, 41, 36, 15, 6, 0], '1947': [0, 1, 2, 17, 68, 36, 35, 18, 7, 0], '1948': [0, 0, 1, 13, 62, 36, 43, 21, 8, 0], '1949': [0, 0, 1, 9, 57, 36, 46, 24, 11, 0], '1950': [0, 0, 1, 7, 49, 39, 45, 32, 11, 0], '1951': [0, 0, 1, 8, 48, 38, 42, 36, 11, 0], '1952': [0, 0, 1, 7, 46, 40, 42, 35, 13, 0], '1953': [0, 0, 0, 5, 45, 42, 39, 36, 17, 0], '1954': [0, 0, 0, 4, 42, 44, 37, 39, 18, 0], '1955': [0, 0, 0, 4, 38, 43, 41, 39, 19, 0], '1956': [0, 0, 0, 3, 35, 47, 39, 40, 20, 0], '1957': [0, 0, 0, 4, 30, 46, 39, 44, 21, 0], '1958': [0, 0, 0, 4, 25, 46, 41, 41, 27, 0], '1959': [0, 0, 0, 3, 27, 43, 37, 45, 29, 0], '1960': [0, 0, 0, 4, 24, 44, 33, 44, 35, 0], '1961': [0, 0, 0, 3, 22, 40, 40, 41, 38, 0], '1962': [0, 0, 0, 1, 18, 43, 41, 43, 38, 0], '1963': [0, 0, 0, 1, 14, 43, 40, 44, 42, 0], '1964': [0, 0, 0, 0, 12, 43, 39, 48, 42, 0], '1965': [0, 0, 0, 0, 12, 41, 38, 50, 43, 0], '1966': [0, 0, 0, 0, 10, 42, 37, 51, 44, 0], '1967': [0, 0, 0, 0, 8, 42, 36, 51, 47, 0], '1968': [0, 0, 0, 0, 7, 41, 38, 50, 48, 0], '1969': [0, 0, 0, 0, 6, 39, 37, 52, 50, 0], '1970': [0, 0, 0, 0, 5, 37, 39, 55, 50, 1], '1971': [0, 0, 0, 0, 3, 35, 41, 51, 56, 1], '1972': [0, 0, 1, 0, 3, 32, 41, 52, 57, 1], '1973': [0, 0, 0, 0, 4, 29, 42, 53, 58, 1], '1974': [0, 0, 0, 0, 1, 30, 42, 47, 66, 1], '1975': [0, 0, 1, 0, 1, 26, 40, 50, 68, 1], '1976': [0, 0, 1, 0, 2, 28, 38, 48, 69, 1], '1977': [0, 0, 1, 0, 0, 26, 37, 47, 74, 2], '1978': [0, 0, 1, 0, 1, 23, 37, 46, 76, 3], '1979': [0, 0, 1, 0, 0, 21, 39, 45, 77, 4], '1980': [0, 0, 0, 0, 0, 22, 37, 46, 77, 5], '1981': [0, 0, 0, 0, 0, 22, 38, 42, 78, 7], '1982': [0, 0, 0, 0, 0, 23, 34, 44, 76, 10], '1983': [0, 0, 0, 0, 2, 17, 34, 45, 79, 10], '1984': [0, 0, 0, 0, 2, 17, 32, 46, 80, 10], '1985': [0, 0, 0, 0, 1, 18, 32, 40, 85, 11], '1986': [0, 0, 0, 0, 0, 17, 33, 40, 83, 14], '1987': [0, 0, 0, 0, 0, 17, 32, 39, 85, 14], '1988': [0, 0, 0, 0, 0, 16, 34, 36, 87, 14], '1989': [0, 0, 0, 0, 0, 15, 32, 37, 89, 14], '1990': [0, 0, 0, 0, 0, 16, 30, 36, 90, 15], '1991': [0, 0, 0, 0, 0, 16, 29, 36, 85, 21], '1992': [0, 0, 0, 0, 0, 15, 27, 39, 84, 22], '1993': [0, 0, 0, 0, 1, 13, 26, 42, 80, 25], '1994': [0, 1, 0, 0, 0, 13, 27, 42, 79, 25], '1995': [0, 0, 0, 0, 0, 13, 28, 42, 78, 26], '1996': [0, 0, 0, 0, 0, 11, 32, 38, 78, 28], '1997': [0, 0, 0, 0, 0, 13, 31, 36, 77, 30], '1998': [0, 0, 0, 0, 0, 12, 30, 37, 76, 32], '1999': [0, 0, 0, 0, 0, 12, 32, 35, 73, 35], '2000': [0, 0, 0, 0, 0, 11, 31, 36, 72, 37], '2001': [0, 0, 0, 0, 0, 10, 32, 34, 73, 38], '2002': [0, 0, 0, 0, 0, 9, 32, 34, 73, 39], '2003': [0, 0, 0, 0, 0, 9, 30, 35, 73, 40], '2004': [0, 0, 0, 0, 0, 7, 31, 36, 70, 43], '2005': [0, 0, 0, 0, 1, 6, 30, 36, 67, 47], '2006': [0, 0, 0, 0, 0, 7, 29, 34, 68, 49], '2007': [0, 0, 0, 0, 0, 6, 28, 34, 68, 51], '2008': [0, 0, 0, 0, 0, 6, 25, 36, 66, 54], '2009': [0, 0, 0, 0, 0, 5, 23, 35, 66, 58], '2010': [0, 0, 0, 1, 0, 4, 22, 35, 63, 62], '2011': [0, 0, 0, 0, 0, 3, 20, 38, 61, 65], '2012': [0, 0, 0, 0, 0, 3, 18, 38, 62, 66], '2013': [0, 0, 0, 0, 0, 2, 15, 40, 63, 67], '2014': [0, 0, 0, 0, 0, 2, 14, 41, 62, 68], '2015': [0, 0, 0, 0, 0, 2, 11, 43, 63, 68], '2016': [0, 0, 0, 0, 0, 2, 6, 44, 65, 70], '2017': [0, 0, 0, 0, 0, 2, 4, 43, 65, 70], '2018': [0, 0, 0, 0, 0, 0, 5, 44, 61, 74]}
Y_MAX = 147
Y_STEP = 29
NUM_BINS = 10

# --- Insights (Auto-Detected) ---
INSIGHTS = [{'time': '1918', 'type': 'peak_shift', 'desc': 'Distribution shifts left'}, {'time': '1919', 'type': 'peak_shift', 'desc': 'Distribution shifts right'}, {'time': '1937', 'type': 'peak_shift', 'desc': 'Distribution shifts right'}, {'time': '1941', 'type': 'peak_shift', 'desc': 'Distribution shifts left'}, {'time': '1942', 'type': 'peak_shift', 'desc': 'Distribution shifts right'}, {'time': '1944', 'type': 'peak_shift', 'desc': 'Distribution shifts left'}, {'time': '1945', 'type': 'peak_shift', 'desc': 'Distribution shifts right'}, {'time': '1954', 'type': 'peak_shift', 'desc': 'Distribution shifts right'}, {'time': '1959', 'type': 'peak_shift', 'desc': 'Distribution shifts right'}, {'time': '1960', 'type': 'peak_shift', 'desc': 'Distribution shifts left'}, {'time': '1961', 'type': 'peak_shift', 'desc': 'Distribution shifts right'}, {'time': '1962', 'type': 'peak_shift', 'desc': 'Distribution shifts left'}, {'time': '1963', 'type': 'peak_shift', 'desc': 'Distribution shifts right'}, {'time': '1971', 'type': 'peak_shift', 'desc': 'Distribution shifts right'}, {'time': '2011', 'type': 'peak_shift', 'desc': 'Distribution shifts right'}]

# --- Story Configuration ---
STORY_TITLE = "Distribution Over Time"
STORY_SUBTITLE = "1800 - 2018"
INCLUDE_INTRO = True
INCLUDE_CONCLUSION = True

# --- Timing (Narrative Style: explainer) ---
INTRO_DURATION = 3.0
REVEAL_DURATION = 2.0
EVOLUTION_DURATION = 22.5
OUTRO_DURATION = 2.5
PER_STEP_TIME = 0.10321100917431193
TOTAL_DURATION = 30.0

# --- Style Configuration ---
BG_COLOR = "#0F0F1A"
TEXT_COLOR = "#FFFFFF"
TEXT_SECONDARY = "#A1A1AA"
PRIMARY_COLOR = "#6366F1"
ACCENT_COLOR = "#22D3EE"

# --- Axis Labels ---
X_LABEL = "Value"
Y_LABEL = "Count"

# --- Layout Constants ---
CHART_WIDTH = 10.0
CHART_HEIGHT = 5.0
BAR_WIDTH_RATIO = 0.7


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def format_number(value: float) -> str:
    """Format large numbers with K/M/B suffixes"""
    if abs(value) >= 1_000_000_000:
        return f"{value / 1_000_000_000:.1f}B"
    elif abs(value) >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    elif abs(value) >= 1_000:
        return f"{value / 1_000:.1f}K"
    else:
        return f"{value:.0f}"


def get_insight_at_time(time_key: str):
    """Get insight at a specific time, if any"""
    for insight in INSIGHTS:
        if insight["time"] == time_key:
            return insight
    return None


# =============================================================================
# SCENE CLASS
# =============================================================================

class GenScene(Scene):
    """
    Story-driven distribution animation.

    Structure:
    1. INTRO: Title and subtitle fade in
    2. REVEAL: Axes and initial bars appear
    3. EVOLUTION: Bars animate through time
    4. HIGHLIGHTS: Insights emphasized during evolution
    5. CONCLUSION: Final state with summary
    """

    def construct(self):
        # Set background
        self.camera.background_color = BG_COLOR

        if not TIMES:
            no_data = Text("No data available", color=TEXT_COLOR)
            self.play(Write(no_data))
            return

        # Track elements
        self.axes = None
        self.bars = None
        self.time_display = None

        # Run story scenes
        if INCLUDE_INTRO:
            self.scene_intro()

        self.scene_reveal()
        self.scene_evolution()

        if INCLUDE_CONCLUSION:
            self.scene_conclusion()

    # -------------------------------------------------------------------------
    # SCENE 1: INTRO
    # -------------------------------------------------------------------------
    def scene_intro(self):
        """Opening scene with title and subtitle."""
        # Create title
        title = Text(
            STORY_TITLE,
            font_size=56,
            color=TEXT_COLOR,
            weight=BOLD,
        )
        title.move_to([0, 0.5, 0])

        # Create subtitle
        subtitle = Text(
            STORY_SUBTITLE,
            font_size=28,
            color=TEXT_SECONDARY,
        )
        subtitle.move_to([0, -0.3, 0])
        subtitle.set_opacity(0.8)

        title_group = VGroup(title, subtitle)

        # Animate entrance
        self.play(
            FadeIn(title, shift=UP * 0.3),
            run_time=0.8,
            rate_func=smooth,
        )
        self.play(
            FadeIn(subtitle, shift=UP * 0.2),
            run_time=0.5,
            rate_func=smooth,
        )

        # Hold
        self.wait(INTRO_DURATION - 1.8)

        # Fade out
        self.play(
            FadeOut(title_group, shift=UP * 0.5),
            run_time=0.5,
        )

    # -------------------------------------------------------------------------
    # SCENE 2: REVEAL
    # -------------------------------------------------------------------------
    def scene_reveal(self):
        """Reveal axes and initial bars."""
        # Create Axes
        self.axes = Axes(
            x_range=[0, NUM_BINS, 1],
            y_range=[0, Y_MAX, Y_STEP],
            x_length=CHART_WIDTH,
            y_length=CHART_HEIGHT,
            axis_config={
                "color": TEXT_SECONDARY,
                "stroke_width": 2,
                "include_ticks": True,
            },
            x_axis_config={
                "include_numbers": False,
            },
            y_axis_config={
                "include_numbers": True,
                "font_size": 18,
            },
            tips=False,
        )
        self.axes.to_edge(DOWN, buff=1.0)
        self.axes.shift(LEFT * 0.5)

        # Custom X-Axis Labels (Bin Ranges)
        x_labels = VGroup()

        if NUM_BINS <= 5:
            label_step = 1
        elif NUM_BINS <= 10:
            label_step = 2
        else:
            label_step = max(1, NUM_BINS // 5)

        for i in range(0, NUM_BINS, label_step):
            label = Text(
                BIN_LABELS[i],
                font_size=14,
                color=TEXT_SECONDARY,
            )
            x_pos = self.axes.c2p(i + 0.5, 0)[0]
            label.move_to([x_pos, self.axes.c2p(0, 0)[1] - 0.4, 0])
            label.rotate(-45 * DEGREES)
            x_labels.add(label)

        # Axis Labels
        x_axis_label = Text(
            X_LABEL,
            font_size=22,
            color=TEXT_SECONDARY,
        )
        x_axis_label.next_to(self.axes.x_axis, DOWN, buff=1.2)

        y_axis_label = Text(
            Y_LABEL,
            font_size=22,
            color=TEXT_SECONDARY,
        )
        y_axis_label.rotate(90 * DEGREES)
        y_axis_label.next_to(self.axes.y_axis, LEFT, buff=0.6)

        # Time Display
        self.time_display = Text(
            str(TIMES[0]),
            font_size=72,
            weight=BOLD,
            color=ACCENT_COLOR,
        )
        self.time_display.to_corner(UL, buff=0.8)
        self.time_display.set_opacity(0.9)

        # Create Initial Bars
        t0 = TIMES[0]
        initial_counts = HISTOGRAMS.get(t0, [0] * NUM_BINS)
        self.bars = self.create_bars(initial_counts)

        # Animate reveal
        self.play(
            Create(self.axes, lag_ratio=0.1),
            run_time=REVEAL_DURATION * 0.4,
        )
        self.play(
            FadeIn(x_labels),
            FadeIn(x_axis_label),
            FadeIn(y_axis_label),
            FadeIn(self.time_display),
            run_time=REVEAL_DURATION * 0.3,
        )
        self.play(
            LaggedStart(
                *[GrowFromEdge(bar, DOWN) for bar in self.bars],
                lag_ratio=0.05,
            ),
            run_time=REVEAL_DURATION * 0.3,
        )

        self.wait(0.3)

    def create_bars(self, counts):
        """Create histogram bars for given counts."""
        bars = VGroup()
        bar_width = (CHART_WIDTH / NUM_BINS) * BAR_WIDTH_RATIO

        for i, count in enumerate(counts):
            if Y_MAX > 0:
                height = (count / Y_MAX) * CHART_HEIGHT
            else:
                height = 0
            height = max(0.01, height)

            bar = RoundedRectangle(
                corner_radius=0.08,
                width=bar_width,
                height=height,
                fill_color=PRIMARY_COLOR,
                fill_opacity=0.85,
                stroke_width=0,
            )

            x_pos = self.axes.c2p(i + 0.5, 0)[0]
            y_pos = self.axes.c2p(0, 0)[1] + height / 2
            bar.move_to([x_pos, y_pos, 0])

            bars.add(bar)

        return bars

    # -------------------------------------------------------------------------
    # SCENE 3: EVOLUTION
    # -------------------------------------------------------------------------
    def scene_evolution(self):
        """Main animation: evolve through time."""
        for step_idx in range(1, len(TIMES)):
            t_current = TIMES[step_idx]
            new_counts = HISTOGRAMS.get(t_current, [0] * NUM_BINS)

            # Check for insights
            insight = get_insight_at_time(t_current)

            # Create new bars
            new_bars = self.create_bars(new_counts)

            # Update time display
            new_time_display = Text(
                str(t_current),
                font_size=72,
                weight=BOLD,
                color=ACCENT_COLOR if insight else ACCENT_COLOR,
            )
            new_time_display.to_corner(UL, buff=0.8)
            new_time_display.set_opacity(0.9)

            # Animate transition
            animations = [Transform(self.time_display, new_time_display)]

            for old_bar, new_bar in zip(self.bars, new_bars):
                animations.append(Transform(old_bar, new_bar))

            self.play(
                *animations,
                run_time=PER_STEP_TIME,
                rate_func=smooth,
            )

            # Show insight if any
            if insight:
                self.show_insight(insight)

    def show_insight(self, insight):
        """Show a highlight annotation for an insight."""
        annotation = Text(
            insight["desc"],
            font_size=24,
            color=ACCENT_COLOR,
            weight=BOLD,
        )
        annotation.to_edge(UP, buff=0.5)

        self.play(
            FadeIn(annotation, shift=DOWN * 0.3),
            run_time=0.3,
        )

        self.wait(0.4)

        self.play(
            FadeOut(annotation),
            run_time=0.3,
        )

    # -------------------------------------------------------------------------
    # SCENE 4: CONCLUSION
    # -------------------------------------------------------------------------
    def scene_conclusion(self):
        """Closing scene with summary."""
        # Calculate summary statistics
        final_counts = HISTOGRAMS.get(TIMES[-1], [0] * NUM_BINS)
        total = sum(final_counts)
        peak_bin = final_counts.index(max(final_counts)) if final_counts else 0
        peak_range = BIN_LABELS[peak_bin] if peak_bin < len(BIN_LABELS) else ""

        # Summary card
        summary = VGroup()

        total_label = Text(
            f"Total: {format_number(total)}",
            font_size=32,
            color=TEXT_COLOR,
            weight=BOLD,
        )

        peak_label = Text(
            f"Peak: {peak_range}",
            font_size=28,
            color=TEXT_SECONDARY,
        )
        peak_label.next_to(total_label, DOWN, buff=0.2)

        summary.add(total_label, peak_label)
        summary.to_corner(UR, buff=0.8)

        # Highlight peak bar
        if peak_bin < len(self.bars):
            peak_bar = self.bars[peak_bin]
            self.play(
                FadeIn(summary, shift=LEFT * 0.3),
                peak_bar.animate.set_fill(ACCENT_COLOR, opacity=0.95),
                run_time=0.5,
            )
        else:
            self.play(
                FadeIn(summary, shift=LEFT * 0.3),
                run_time=0.5,
            )

        # Hold
        self.wait(OUTRO_DURATION - 0.5)
