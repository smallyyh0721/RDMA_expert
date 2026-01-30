# NVIDIA ConnectX-5 Ethernet Adapter Cards User Manual - NVIDIA Docs

Source: https://docs.nvidia.com/networking/display/connectx5en

---

The ConnectX-5 product line has moved to end-of-life.

About This Manual

This User Manual describes NVIDIA® ConnectX®-5 and ConnectX®-5 Ex Ethernet Single and Dual SFP28 and QSFP28 port PCI Express x8/x16 adapter cards. It provides details as to the interfaces of the board, specifications, required software and firmware for operating the board, and relevant documentation.

EOL'ed (End of Life) Ordering Part Numbers

IC in Use

NVIDIA SKU

Legacy OPN

Marketing Description

ConnectX®-5 Ex

900-9X5AZ-0053-ST5

MCX512A-ADAT

ConnectX®-5ExEN network interface card,25GbEdual-port SFP28, PCIe Gen3.0/4.0 x8, tall bracket

900-9X5AD-0056-ST7

MCX516A-CDAT

ConnectX®-5ExEN network interface card,100GbEdual-port QSFP28, PCIe Gen4.0x16, tall bracket

900-9X5AD-0054-ST0

MCX516A-BDAT

ConnectX®-5ExEN network interface card,40GbEdual-port QSFP28, PCIe Gen4.0 x16, tall bracket

ConnectX®-5

900-9X5AZ-0053-0T3

MCX512A-ACAT

ConnectX®-5 EN network interface card,25GbEdual-port SFP28, PCIe Gen3.0 x8, tall bracket

900-9X5AZ-0053-ST4

MCX512A-ACUT

ConnectX®-5 EN network interface card,10/25GbEdual-port SFP28, PCIe Gen3.0 x8,UEFI Enabled (x86/Arm), tall bracket

900-9X5AZ-0053-ST6

MCX512F-ACAT

ConnectX®-5 EN network interface card,25GbEdual-port SFP28, PCIe Gen3.0 x16, tall bracket

900-9X5AZ-0053-ST0

MCX512F-ACHT

ConnectX®-5 EN network interface card,with host management,25GbEDual-port SFP28, PCIe Gen3.0 x16,UEFI Enabled, tall bracket

900-9X5AD-0015-ST0

MCX515A-GCAT

ConnectX®-5 EN network interface card,50GbEsingle-port QSFP28, PCIe Gen3.0 x16, tall bracket

900-9X5AD-0055-ST0

MCX516A-GCAT

ConnectX®-5 EN network interface card,50GbEdual-port QSFP28, PCIe Gen3.0 x16, tall bracket

900-9X5AD-0016-ST1

MCX515A-CCAT

ConnectX®-5 EN network interface card,100GbEsingle-port QSFP28, PCIe Gen3.0 x16, tall bracket

900-9X5AD-0016-ST2

MCX515A-CCUT

ConnectX®-5 EN network interface card,100GbEsingle-port QSFP28, PCIe Gen3.0 x16,UEFI Enabled (Arm, x86),tall bracket

900-9X5AD-0056-ST6

MCX516A-CCHT

ConnectX®-5 EN network interface card, withhost management100GbEdual-port QSFP28, PCIe Gen3.0 x16,UEFI Enabled, tall bracket

900-9X5AD-0056-ST1

MCX516A-CCAT

ConnectX®-5 EN network interface card,100GbEdual-port QSFP28, PCIe Gen3.0 x16, tall bracket

Intended Audience

This manual is intended for the installer and user of these cards. The manual assumes basic familiarity with Ethernet network and architecture specifications.

Technical Support

Customers who purchased NVIDIA products directly from NVIDIA are invited to contact us through the following methods:

URL:https://www.nvidia.com> SupportE-mail:enterprisesupport@nvidia.com

Customers who purchased NVIDIA Global Support Services, please see your contract for details regarding Technical Support.Customers who purchased NVIDIA products through an NVIDIA-approved reseller should first seek assistance through their reseller.Related Documentation

MLNX_OFED for Linux User Manual and Release Notes

User Manual describing OFED features, performance, band diagnostic, tools content, and configuration. SeeMLNX_OFED for Linux Documentation.

WinOF-2 for Windows User Manual and Release Notes

User Manual describing WinOF-2 features, performance, Ethernet diagnostic, tools content, and configuration. SeeWinOF-2 for Windows Documentation.

NVIDIA VMware for Ethernet User Manual

User Manual and release notes describing the various components of the NVIDIA ConnectX® NATIVE ESXi stack. SeeVMware® ESXi Drivers Documentation.

NVIDIA Firmware Utility (mlxup) User Manual and Release Notes

NVIDIA firmware update and query utility used to update the firmware. Refer toFirmware Utility (mlxup) Documentation.

NVIDIA Firmware Tools (MFT) User Manual

User Manual describing the set of MFT firmware management tools for a single node. SeeMFT User Manual.

IEEE Std 802.3 Specification

IEEE Ethernet Specifications

PCI Express Specifications

Industry Standard PCI Express Base and Card Electromechanical Specifications. Refer toPCI-SIG Specifications.

LinkX Interconnect Solutions

NVIDIA LinkX Ethernet cables and transceivers are designed to maximize the performance of High-Performance Computing networks, requiring high-bandwidth, low-latency connections between compute nodes and switch nodes. NVIDIA offers one of the industry’s broadest portfolios of 40Gb/s, 56Gb/s and 100Gb/s cables, including Direct Attach Copper cables (DACs), copper splitter cables, Active Optical Cables (AOCs) and transceivers in a wide range of lengths from 0.5m to 10km. In addition to meeting Ethernet standards, NVIDIA tests every product in an end-to-end environment ensuring a Bit Error Rate of less than 1E-15. Read more atLinkX® Ethernet Cables and Transceivers.

Document Conventions

When discussing memory sizes, MB and MBytes are used in this document to mean size in MegaBytes. The use of Mb or Mbits (small b) indicates size in MegaBits. In this document, PCIe is used to mean PCI Express.

Revision History

A list of the changes made to this document are provided inDocument Revision History.

