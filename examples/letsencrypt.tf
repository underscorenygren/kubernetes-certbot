variable "region" { }

variable "account_id" {}

# The name of the cluster
variable "name" { }

output "access_key_id" {
  value = "${aws_iam_access_key.key.id}"
}

output "secret_access_key" {
  value = "${aws_iam_access_key.key.secret}"
}

output "user_name" {
  value = "${aws_iam_user.user.name}"
}

provider "aws" {
  region = "${var.region}"
}

resource "aws_iam_user" "user" {
  name = "${var.name}-letsencrypt"
}

resource "aws_iam_access_key" "key" {
  user = "${aws_iam_user.user.name}"
}

resource "aws_iam_user_policy" "elb-update" {
  name = "${var.name}-elb-update-policy"
  user = "${aws_iam_user.user.name}"
  policy = <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
          "Action": [
            "elasticloadbalancing:SetLoadBalancerListenerSSLCertificate"
          ],
          "Effect": "Allow",
          "Resource": [
            "arn:aws:elasticloadbalancing:${var.region}:${var.account_id}:loadbalancer/*"
          ]
        }
    ]
}
EOF
}

# The describe endpoints have to be * for some reason
resource "aws_iam_user_policy" "elb-describe" {
  name = "${var.name}-elb-describe-policy"
  user = "${aws_iam_user.user.name}"
  policy = <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
          "Action": [
            "elasticloadbalancing:DescribeLoadBalancerAttributes"
          ],
          "Effect": "Allow",
          "Resource": "*"
        }
    ]
}
EOF
}

resource "aws_iam_user_policy" "server-certificate-edit" {
  name = "${var.name}-server-certificate-edit"
  user = "${aws_iam_user.user.name}"
  policy = <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
          "Action": [
            "iam:DeleteServerCertificate",
            "iam:GetServerCertificate",
            "iam:ListServerCertificates",
            "iam:UploadServerCertificate"
          ],
          "Effect": "Allow",
          "Resource": "arn:aws:iam::${var.account_id}:server-certificate/${var.name}-*"
        }
    ]
}
EOF
}
