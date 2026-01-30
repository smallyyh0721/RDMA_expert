# Troubleshooting - NVIDIA Docs

Source: https://docs.nvidia.com/networking/display/connectx6dxen/troubleshooting

---


#### On This Page

General TroubleshootingLinux TroubleshootingWindows Troubleshooting


# Troubleshooting


## General Troubleshooting

Server unable to find the adapter

Ensure that the adapter is placed correctlyMake sure the adapter slot and the adapter are compatibleInstall the adapter in a different PCI Express slotUse the drivers that came with the adapter or download the latestMake sure your motherboard has the latest BIOSTry to reboot the server

Ensure that the adapter is placed correctly

Make sure the adapter slot and the adapter are compatible

Install the adapter in a different PCI Express slot

Use the drivers that came with the adapter or download the latest

Make sure your motherboard has the latest BIOS

Try to reboot the server

The adapter no longer works

Reseat the adapter in its slot or a different slot, if necessaryTry using another cableReinstall the drivers for the network driver files may be damaged or deletedReboot the server

Reseat the adapter in its slot or a different slot, if necessary

Try using another cable

Reinstall the drivers for the network driver files may be damaged or deleted

Reboot the server

Adapters stopped working after installing another adapter

Try removing and re-installing all adaptersCheck that cables are connected properlyMake sure your motherboard has the latest BIOS

Try removing and re-installing all adapters

Check that cables are connected properly

Make sure your motherboard has the latest BIOS

Link indicator light is off

Try another port on the switchMake sure the cable is securely attachedCheck you are using the proper cables that do not exceed the recommended lengthsVerify that your switch and adapter port are compatible

Try another port on the switch

Make sure the cable is securely attached

Check you are using the proper cables that do not exceed the recommended lengths

Verify that your switch and adapter port are compatible

Link light is on, but with no communication established

Check that the latest driver is loadedCheck that both the adapter and its link are set to the same speed and duplex settings

Check that the latest driver is loaded

Check that both the adapter and its link are set to the same speed and duplex settings

Event message received of insufficient power

When [ adapter's current power consumption ] > [ PCIe slot advertised power limit ] – a warning message appears in the server's system even logs (Eg. dmesg: "Detected insufficient power on the PCIe slow")It's recommended to use a PCIe slot that can supply enough power.If a message of the following format appears – "mlx5_core 0003:01:00.0: port_module:254:(pid 0): Port module event[error]: module 0, Cable error, One or more network ports have been powered down due to insufficient/unadvertised power on the PCIe slot" please upgrade your Adapter's firmware.If the message remains – please consider switching from Active Optical Cable (AOC) or transceiver to Direct Attached Copper (DAC) connectivity.

When [ adapter's current power consumption ] > [ PCIe slot advertised power limit ] – a warning message appears in the server's system even logs (Eg. dmesg: "Detected insufficient power on the PCIe slow")

It's recommended to use a PCIe slot that can supply enough power.

If a message of the following format appears – "mlx5_core 0003:01:00.0: port_module:254:(pid 0): Port module event[error]: module 0, Cable error, One or more network ports have been powered down due to insufficient/unadvertised power on the PCIe slot" please upgrade your Adapter's firmware.

If the message remains – please consider switching from Active Optical Cable (AOC) or transceiver to Direct Attached Copper (DAC) connectivity.


## Linux Troubleshooting

Environment Information

cat /etc/issue

uname -acat /proc/cupinfo | grep ‘model name’ | uniqofed_info -sifconfig -aip link showethtool <interface>ethtool -i <interface_of_Mellanox_port_num>ibdev2netdev

Card Detection

lspci | grep -i Mellanox

Mellanox Firmware Tool (MFT)

Download and install MFT:MFT Documentation

Refer to the User Manual for installation instructions.Once installed, run:mst startmst statusflint -d <mst_device> q

Ports Information

ibstat

ibv_devinfo

Firmware Version Upgrade

To download the latest firmware version, refer to theNVIDIA Update and Query Utility.

Collect Log File

cat /var/log/messages

dmesg >> system.logjournalctl (Applicable on new operating systems)cat /var/log/syslog


## Windows Troubleshooting

Environment Information

From the Windows desktop choose the Start menu and run:msinfo32

```
msinfo32
```

To export system information to a text file, choose the Export option from the File menu.Assign a file name and save.

Mellanox Firmware Tool (MFT)

Download and install MFT:MFT Documentation

Refer to the User Manual for installation instructions.Once installed, open a CMD window and run:WinMFTmst startmst statusflint –d <mst_device> q

Ports Information

vstat

Firmware Version Upgrade

Download the latest firmware version using the PSID/board ID fromhere.

flint –d <mst_device> –i <firmware_bin_file> b

Collect Log File

Event log viewerMST device logs:mst startmst statusflint –d <mst_device> dc > dump_configuration.logmstdump <mst_device> dc > mstdump.log

Event log viewer

MST device logs:

mst startmst status

mst start

mst status

flint –d <mst_device> dc > dump_configuration.log

mstdump <mst_device> dc > mstdump.log

