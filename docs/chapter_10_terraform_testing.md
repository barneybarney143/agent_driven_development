# Chapter 10.0 - Comprehensive Terraform Testing Frameworks

## The Imperative of Multi-Layered Terraform Testing

In NetDevOps, deploying infrastructure as code carries significant responsibility. Errors in Terraform configurations can lead to costly outages, security vulnerabilities, or unintended resource consumption. Therefore, a robust, multi-layered testing strategy is not merely a best practice; it is a mandatory quality gate. Terraform testing must encompass hygiene checks, unit validation, security compliance, and full integration testing to ensure that infrastructure deployments are reliable, secure, and meet organizational standards.

This chapter details the frameworks and methodologies required to implement a comprehensive testing strategy for Terraform configurations.

## 10.1 Hygiene and Linting

Before any state changes are planned or applied, the Terraform configuration must undergo basic hygiene and static analysis checks. These checks are fast, local, and provide immediate feedback to the developer, preventing common errors and enforcing coding standards.

*   **`terraform fmt -check`**: Ensures consistent formatting of HCL code. This command checks if all `.tf` files in the current directory are properly formatted according to Terraform's canonical style. Using `-check` makes it non-interactive and suitable for CI/CD pipelines, failing if any files are not formatted correctly.
    ```bash
    terraform fmt -check -recursive
    ```

*   **`terraform validate`**: Verifies the configuration syntax correctness and proper module references. It checks for syntactical errors, invalid variable types, and ensures that all required providers and modules are correctly referenced. This does not interact with remote state or real infrastructure.
    ```bash
    terraform validate
    ```

*   **`tflint`**: A pluggable and extensible linter for Terraform. `tflint` goes beyond syntax checks to enforce organizational best practices, such as verifying that engineers utilize Terraform variables instead of hard-coding values, ensuring resource tags are present, or flagging deprecated syntax. It helps catch common anti-patterns that can lead to environment drift or maintenance headaches.
    ```bash
    tflint --recursive
    ```
    `tflint` can be configured with a `.tflint.hcl` file to enable/disable rules or define custom checks.

## 10.2 Unit and Integration Testing with the Native Framework

For testing Terraform module logic and ensuring that resources are configured as intended, the **native Terraform Testing Framework** is the recommended approach. While established tools like Terratest are powerful and flexible, the native framework offers greater consistency, a more prescriptive HCL-native approach, and reduces the overhead of maintaining Go code required by Terratest.

Tests are defined in `.tftest.hcl` files within your module or root configuration. These tests assert against the planned output (before deployment) or the deployed resource attributes (after deployment). For basic validity, tests can ensure that the configuration results in a valid plan, but for unit testing, the focus shifts to advanced techniques.

```terraform
# modules/vpc_segment/vpc_segment_test.tftest.hcl
resource "random_pet" "name" {}

run "vpc_creation" {
  module "vpc" {
    source = "."
    name        = random_pet.name.id
    cidr_block  = "10.0.0.0/16"
    subnet_cidrs = ["10.0.1.0/24", "10.0.2.0/24"]
    tags = {
      Environment = "test"
    }
  }

  assert {
    condition     = module.vpc.vpc_id != null
    error_message = "VPC ID should not be null after creation"
  }

  assert {
    condition     = length(module.vpc.public_subnet_ids) == 2
    error_message = "Should create 2 public subnets"
  }

  assert {
    condition     = module.vpc.vpc_cidr_block == "10.0.0.0/16"
    error_message = "VPC CIDR block mismatch"
  }
}
```

To run native tests:
```bash
terraform test
```

## 10.3 Advanced Testing: Provider Mocking and Resource Overrides

The ability to test IaC modules without deploying real, expensive, and slow infrastructure is a fundamental shift in quality assurance. The native framework's **mocking capabilities** enable instantaneous, cost-effective unit testing, drastically shortening the feedback loop.

*   **Provider Mocking:** Engineers must learn how to define a `mock_provider` alongside the real provider configuration. This fake provider is assigned an alias. In the `run` block of a test, the `providers` attribute is then used to explicitly instruct Terraform to utilize the mocked provider instead of the real one. When using a mocked provider, required resource attributes must be set, but Terraform automatically generates values for optional computed attributes (e.g., strings become a random 8-character string, numbers become 0).

    ```terraform
    # .tftest.hcl
    mock_provider "aws" {
      # Define mock behavior for AWS resources
      # For example, to mock an aws_vpc resource:
      resource "aws_vpc" "example" {
        id         = "vpc-mocked123"
        cidr_block = "10.0.0.0/16"
        tags       = {"Name" = "mock-vpc"}
      }
    }

    run "mocked_vpc_test" {
      providers = {
        aws = aws.mocked # Use the mocked AWS provider
      }
      module "vpc" {
        source = "."
        name        = "test-vpc"
        cidr_block  = "10.1.0.0/16"
        subnet_cidrs = ["10.1.1.0/24"]
      }

      assert {
        condition     = module.vpc.vpc_id == "vpc-mocked123"
        error_message = "Mocked VPC ID should match"
      }
    }
    ```

*   **Resource and Module Overrides:** To achieve surgical unit testing, the specification requires the use of `override_resource`, `override_data`, and `override_module` blocks within a `run` block.
    *   `override_resource`: Used to inject specific values for a resource, preventing the underlying provider from being called. This is useful for testing logic that depends on resource attributes without actually creating the resource.
    *   `override_data`: Used to simulate output from a data source, allowing tests to proceed without making API calls to fetch external data.
    *   `override_module`: Used to simulate the outputs of an entire module without executing the module's resources. This is crucial for testing a parent module's logic without deploying all its child modules.

    ```terraform
    run "module_override_example" {
      module "parent_module" {
        source = "./parent_module"
        # ... input variables ...
      }

      override_module "parent_module.child_vpc_module" {
        outputs = {
          vpc_id = "vpc-override-123"
          subnet_ids = ["subnet-override-a", "subnet-override-b"]
        }
      }

      assert {
        condition     = module.parent_module.vpc_id_from_child == "vpc-override-123"
        error_message = "Parent module should use overridden child VPC ID"
      }
    }
    ```

This strategy allows engineers to achieve instantaneous, cost-effective unit testing, drastically shortening the feedback loop compared to older methodologies that required infrastructure creation.

## 10.4 Compliance and Negative Testing

Configuration must not only be functionally correct but also comply with security and organizational standards. This requires policy enforcement and negative testing.

*   **Policy Enforcement (Checkov / `terraform-compliance`):** The use of compliance tools like **Checkov** and **`terraform-compliance`** is mandatory. These tools analyze the Terraform configuration (or the plan output) against a set of predefined security policies and best practices. They can detect issues such as:
    *   Exposed ports in security groups.
    *   Weak encryption settings for storage buckets.
    *   Missing logging configurations.
    *   Non-compliant resource tagging.

    ```bash
    # Example Checkov run
    checkov -d . --framework terraform

    # Example terraform-compliance run (requires a plan.json)
    terraform plan -out tfplan.binary
    terraform show -json tfplan.binary > tfplan.json
    terraform-compliance -p tfplan.json -f features/
    ```

*   **Behavioral Driven Development (BDD) and Negative Testing:** `terraform-compliance` allows for negative testing—validating that the code *does not* introduce undesirable conditions. This is achieved by writing human-readable feature files using **Gherkin syntax**.

    **Use Case:** Ensuring all network interfaces provisioned in a cloud environment do not have public IP addresses.

    ```gherkin
    # features/no_public_ips.feature
    Feature: Network interfaces should not have public IPs

      Scenario: Ensure no public IP addresses are assigned to network interfaces
        When I create an aws_network_interface
        Then it must not have public_ip_address configured

      Scenario: Ensure no public IP addresses are assigned to EC2 instances
        When I create an aws_instance
        Then it must not have associate_public_ip_address configured
    ```

Integrating these tools ensures that the implemented IaC follows internal standards and security benchmarks prior to deployment, providing a critical layer of automated governance.

## Terraform Testing Framework Matrix

| Framework/Tool           | Primary Testing Focus             | Execution Requirement           | Key Advantage                                                                                                 |
| :----------------------- | :-------------------------------- | :------------------------------ | :------------------------------------------------------------------------------------------------------------ |
| `terraform validate` / `fmt` | Syntax and Configuration Hygiene  | Pre-deploy (Local)              | Speed and consistency; mandatory developer checks.                                                            |
| Native Testing Framework | Unit/Integration Testing (HCL)    | Plan/Apply (Supports Mocking)   | Built-in, HCL-native tests; essential for fast, resource-less unit testing via mocking.                       |
| Terratest (Go)           | End-to-End/Integration Testing    | Apply (Requires Real Infrastructure) | High flexibility; suitable for complex, cross-module orchestration and external verification.                 |
| Checkov / `terraform-compliance` | Policy, Security, and Compliance  | Plan/Pre-deploy (Local/CI)      | Enforces security standards and organizational policies (negative testing).                                   |
