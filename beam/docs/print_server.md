# Print Server

There are several steps to get a print server connected in ERPNext. First, the `pycups` dependency needs to be installed on the system, which in turn depends on the CUPS project's `libcups` library. See the following links for installation instructions:

- [OpenPrinting CUPS installation and configuration instructions](https://github.com/OpenPrinting/cups/blob/master/INSTALL.md)
- [PyCUPS dependencies, compiling, and installation information](https://github.com/OpenPrinting/pycups)

Next, the user must create a new Network Printer Settings document and fill in the information.

![Screen shot of the Network Printer Settings document fields, including Name, Printer Namem Server IP, and Port.](./assets/network_printer_settings.png)
