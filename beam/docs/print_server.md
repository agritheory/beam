# Print Server

There are several steps to get a print server connected in ERPNext.

1. First, the `pycups` dependency needs to be installed on the system, which in turn depends on the CUPS project's `libcups` library. See the following links for installation instructions:
- [OpenPrinting CUPS installation and configuration instructions](https://github.com/OpenPrinting/cups/blob/master/INSTALL.md)
- [PyCUPS dependencies, compiling, and installation information](https://github.com/OpenPrinting/pycups)

2. Next, the user must add their Zebra printer to the CUPS server. This can be done by following the official CUPS documentation, which can be found [here](https://supportcommunity.zebra.com/s/article/Adding-a-Zebra-Printer-in-a-CUPS-Printing-System).

3. The user must also create a new `Network Printer Settings` document and fill in the relevant information.

![Screen shot of the Network Printer Settings document fields, including Name, Printer Name, Server IP, and Port.](./assets/network_printer_settings.png)
