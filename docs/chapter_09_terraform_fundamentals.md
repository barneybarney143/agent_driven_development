# Chapter 9.0 - Terraform Fundamentals for Network Infrastructure Deployment

## Introduction to Terraform for Stateful Infrastructure

While Ansible excels at configuration management and imperative task execution, **Terraform** is the industry-standard tool for provisioning and managing infrastructure in a *stateful* and *declarative* manner. For network engineers, Terraform is essential for deploying and managing network infrastructure components that are typically provisioned rather than configured, such as:

*   Virtual Networks (VNETs, VPCs) in cloud environments.
*   Cloud connectivity services (VPN gateways, Direct Connect/ExpressRoute).
*   Load balancers and application delivery controllers.
*   SaaS firewall policies and security groups.
*   DNS records and IP address management (IPAM) entries.

Terraform's declarative approach means you describe the *desired end-state* of your infrastructure, and Terraform figures out the necessary steps to achieve that state. This contrasts with Ansible's more procedural approach, making Terraform particularly powerful for managing the lifecycle of infrastructure resources.

## Core Terraform Competencies

To effectively leverage Terraform in a NetDevOps context, a foundational understanding of its core concepts is crucial:

### 1. Providers and Resources

*   **Providers:** Terraform interacts with various cloud platforms, SaaS offerings, and on-premises APIs through **providers**. A provider is a plugin that understands the API interactions for a specific service (e.g., AWS, Azure, Google Cloud, Cisco ACI, F5 BIG-IP, VMware vSphere). You declare which providers your configuration will use.

    ```terraform
    # main.tf
    terraform {
      required_providers {
        aws = {
          source  = "hashicorp/aws"
          version = "~> 5.0"
        }
        # Example for a network vendor provider
        aci = {
          source  = "CiscoDevNet/aci"
          version = "~> 2.0"
        }
      }
    }

    provider "aws" {
      region = "us-east-1"
    }

    provider "aci" {
      apic_host = "{{ var.apic_ip }}"
      username  = "{{ var.apic_username }}"
      password  = "{{ var.apic_password }}"
      insecure  = true
    }
    ```

*   **Resources:** A **resource** is the most fundamental building block in Terraform. It represents a single infrastructure object (e.g., a virtual machine, a network interface, a security group, a VLAN, a BGP peer). Resources are declared using a `resource` block, specifying the provider and the type of resource, along with its desired attributes.

    ```terraform
    # main.tf
    resource "aws_vpc" "main" {
      cidr_block = "10.0.0.0/16"
      tags = {
        Name = "production-vpc"
      }
    }

    resource "aci_bridge_domain" "app_bd" {
      tenant_dn = "uni/tn-{{ var.tenant_name }}"
      name      = "app-bd"
      description = "Bridge Domain for Application Tier"
    }
    ```

### 2. Modules

**Modules** are reusable, version-controlled units of Terraform configuration. They allow you to encapsulate and abstract common infrastructure patterns, promoting the **DRY (Don't Repeat Yourself)** principle. Instead of writing the same VPC or firewall policy configuration repeatedly, you create a module and simply call it, passing in specific parameters.

Modules can be sourced from local paths, Git repositories, or the Terraform Registry. They typically consist of:
*   **Input Variables:** Parameters that customize the module's behavior.
*   **Resources:** The actual infrastructure components the module provisions.
*   **Output Values:** Data exposed by the module for use by other parts of the configuration.

```terraform
# Calling a module to create a standardized VPC
module "network_segment_prod" {
  source = "./modules/vpc_segment"

  name        = "prod-segment"
  cidr_block  = "10.10.0.0/16"
  subnet_cidrs = [
    "10.10.1.0/24",
    "10.10.2.0/24"
  ]
  tags = {
    Environment = "Production"
  }
}

# Calling a module to configure a standard BGP peer on a network device
module "bgp_peer_core_rtr" {
  source = "git::https://github.com/your-org/terraform-network-modules.git//bgp_peer?ref=v1.0.0"

  device_ip     = "192.168.1.1"
  local_as      = 65000
  peer_ip       = "192.168.1.2"
  remote_as     = 65001
  description   = "Peer to Edge Router"
}
```

### 3. State Management

The **Terraform state file** (`terraform.tfstate`) is arguably the most critical component of a Terraform deployment. It is a JSON file that acts as the single source of truth for your infrastructure. It tracks:

*   **Real-world infrastructure:** A mapping of the resources defined in your configuration to the actual infrastructure objects provisioned in the cloud or on-premises.
*   **Metadata:** Attributes of the managed resources (e.g., resource IDs, IP addresses, ARN values).

The state file is crucial because:
*   **Mapping:** It allows Terraform to know which real-world resources correspond to your configuration.
*   **Performance:** It avoids needing to query the remote API for every attribute during `terraform plan`.
*   **Drift Detection:** By comparing the state file to the current configuration and the actual infrastructure, Terraform can detect and report configuration drift.

**Criticality:** The state file must be stored securely, backed up, and, for collaborative environments, managed remotely (e.g., in an S3 bucket, Azure Blob Storage, or Terraform Cloud/Enterprise). Remote state backends provide locking mechanisms to prevent concurrent modifications and data corruption, which is vital for team collaboration.

### 4. Loop Constructs (`count` and `for_each`)

To provision multiple identical or similar resources efficiently, Terraform provides **loop constructs**:

*   **`count` Meta-Argument:** Used when you need to create multiple instances of a resource that are largely identical, and you can refer to them by an index (e.g., `resource.type[0]`, `resource.type[1]`).

    **Use Case:** Provisioning multiple identical VNETs across different regions or multiple similar firewall rules.

    ```terraform
    variable "regions" {
      description = "List of AWS regions to deploy VPCs"
      type        = list(string)
      default     = ["us-east-1", "us-west-2"]
    }

    resource "aws_vpc" "regional_vpc" {
      count      = length(var.regions)
      cidr_block = "10.${count.index}.0.0/16"
      tags = {
        Name   = "Regional-VPC-${var.regions[count.index]}"
        Region = var.regions[count.index]
      }
    }
    ```

*   **`for_each` Meta-Argument:** Used when you need to create multiple instances of a resource based on a map or a set of strings, and you want to refer to them by a meaningful key (e.g., `resource.type["web"]`, `resource.type["db"]`). This is generally preferred over `count` when the items have unique identifiers.

    **Use Case:** Provisioning multiple security groups, each with a unique name and specific rules, or configuring multiple BGP neighbors where each neighbor has a distinct IP address and AS number.

    ```terraform
    variable "security_groups" {
      description = "Map of security group configurations"
      type = map(object({
        description = string
        ingress_ports = list(number)
      }))
      default = {
        "web" = {
          description = "Web Server Security Group"
          ingress_ports = [80, 443]
        },
        "db" = {
          description = "Database Security Group"
          ingress_ports = [3306, 5432]
        }
      }
    }

    resource "aws_security_group" "app_sgs" {
      for_each    = var.security_groups
      name        = "${each.key}-sg"
      description = each.value.description
      vpc_id      = aws_vpc.main.id

      ingress {
        from_port   = port
        to_port     = port
        protocol    = "tcp"
        cidr_blocks = ["0.0.0.0/0"]
        for_each    = each.value.ingress_ports
        content     = port
      }
    }
    ```

By mastering these fundamental concepts, network engineers can effectively provision and manage their network infrastructure as code, ensuring consistency, scalability, and auditability across their entire environment.