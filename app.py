import os
import logging
from flask import Flask, render_template, request, jsonify, send_file
from datetime import datetime
import tempfile
import json

# Import utility modules
from ssm_utils import get_nubinix_clients, get_credentials_for_client, get_client_billing_data
from aws_utils import discover_aws_resources
from azure_utils import discover_azure_resources
from report_generator import generate_comprehensive_report
from cleanup_service import schedule_post_report_cleanup, force_immediate_cleanup

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")

# Set debug mode
app.config['DEBUG'] = True


@app.route('/')
def index():
    """Serve the main application page."""
    return '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Nubinix Cloud Insights</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <script src="https://unpkg.com/lucide@latest/dist/umd/lucide.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }

            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: #f8fafc;
                line-height: 1.6;
            }

            .container {
                max-width: 1200px;
                margin: 0 auto;
                padding: 0 20px;
            }

            .header {
                background: white;
                border-bottom: 1px solid #e2e8f0;
                padding: 1rem 0;
            }

            .header-content {
                display: flex;
                justify-content: space-between;
                align-items: center;
            }

            .logo {
                display: flex;
                align-items: center;
                gap: 12px;
                font-size: 24px;
                font-weight: bold;
                color: #1e293b;
            }

            .logo img {
                height: 40px;
                width: auto;
            }

            .tagline {
                color: #64748b;
                font-size: 14px;
                font-weight: normal;
            }

            /* Button Styles - Matching React Design */
            .btn {
                display: inline-flex;
                align-items: center;
                justify-content: center;
                gap: 8px;
                padding: 10px 20px;
                border: none;
                border-radius: 6px;
                font-size: 14px;
                font-weight: 500;
                cursor: pointer;
                transition: all 0.2s ease-in-out;
                text-decoration: none;
                white-space: nowrap;
                position: relative;
                overflow: hidden;
            }

            .btn:disabled {
                pointer-events: none;
                opacity: 0.5;
            }

            .btn:focus-visible {
                outline: none;
                box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.5);
            }

            /* Button Gradient - Exact match */
            .button-gradient {
                background: linear-gradient(135deg, #3DB3E3 0%, #6866C1 50%, #E865A0 100%);
                color: white;
                border: none;
            }

            .button-gradient:hover {
                opacity: 0.9;
                transform: translateY(-1px);
                box-shadow: 0 4px 12px rgba(61, 179, 227, 0.3);
            }

            .btn-primary {
                background: linear-gradient(135deg, #000000 0%, #1f2937 30%, #374151 70%, #9ca3af 100%);
                color: white;
                position: relative;
                overflow: hidden;
                z-index: 1;
            }

            .btn-primary::before {
                content: '';
                position: absolute;
                top: 50%;
                left: 50%;
                width: 0;
                height: 0;
                background: linear-gradient(135deg, #3DB3E3 0%, #6866C1 50%, #E865A0 100%);
                border-radius: 50%;
                transition: all 0.4s ease;
                transform: translate(-50%, -50%);
                z-index: -1;
            }

            .btn-primary:hover::before {
                width: 300px;
                height: 300px;
            }

            .btn-primary:hover {
                color: white;
                transform: translateY(-2px);
                box-shadow: 0 8px 25px rgba(0, 0, 0, 0.3);
            }

            /* Button Black Bubble Effect */
            .button-black-bubble {
                background: #000;
                color: white;
                position: relative;
                overflow: hidden;
                z-index: 1;
            }

            .button-black-bubble::before {
                content: '';
                position: absolute;
                top: 50%;
                left: 50%;
                width: 0;
                height: 0;
                background: linear-gradient(135deg, #3DB3E3 0%, #6866C1 50%, #E865A0 100%);
                border-radius: 50%;
                transition: all 0.4s ease;
                transform: translate(-50%, -50%);
                z-index: -1;
            }

            .button-black-bubble:hover::before {
                width: 300px;
                height: 300px;
            }

            .button-black-bubble:hover {
                color: white;
                transform: translateY(-2px);
                box-shadow: 0 8px 25px rgba(0, 0, 0, 0.3);
            }

            .btn-outline {
                background: transparent;
                color: #64748b;
                border: 1px solid #e2e8f0;
            }

            .btn-outline:hover {
                background: #f1f5f9;
                color: #1e293b;
                border-color: #cbd5e1;
            }

            .btn-destructive {
                background: #ef4444;
                color: white;
            }

            .btn-destructive:hover {
                background: #dc2626;
                transform: translateY(-1px);
            }

            /* Step Indicator Styles */
            .step-active {
                background: #8B5CF6;
                color: white;
                box-shadow: 0 4px 12px rgba(139, 92, 246, 0.3);
            }

            .step-completed {
                background: #10b981;
                color: white;
                box-shadow: 0 2px 8px rgba(16, 185, 129, 0.3);
            }

            .step-inactive {
                background: #D1D5DB;
                color: #6B7280;
            }

            .card {
                background: white;
                border-radius: 12px;
                box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
                padding: 32px;
                margin: 20px 0;
                transition: all 0.3s ease;
            }

            .card:hover {
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
            }

            .title {
                font-size: 32px;
                font-weight: 700;
                text-align: center;
                margin-bottom: 12px;
                background: linear-gradient(135deg, #3DB3E3 0%, #6866C1 50%, #E865A0 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
                animation: gradientShift 3s ease-in-out infinite;
            }

            @keyframes gradientShift {
                0%, 100% { background-position: 0% 50%; }
                50% { background-position: 100% 50%; }
            }

            .subtitle {
                text-align: center;
                color: #64748b;
                margin-bottom: 40px;
            }

            .provider-grid {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 20px;
                max-width: 600px;
                margin: 0 auto;
            }

            .provider-card {
                border: 2px solid #e2e8f0;
                border-radius: 12px;
                padding: 24px;
                text-align: center;
                cursor: pointer;
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                background: white;
                position: relative;
                overflow: hidden;
            }

            .provider-card::before {
                content: '';
                position: absolute;
                top: 0;
                left: -100%;
                width: 100%;
                height: 100%;
                background: linear-gradient(90deg, transparent, rgba(61, 179, 227, 0.1), transparent);
                transition: left 0.5s ease;
            }

            .provider-card:hover::before {
                left: 100%;
            }

            .provider-card:hover {
                border-color: #3DB3E3;
                transform: translateY(-4px);
                box-shadow: 0 8px 25px rgba(61, 179, 227, 0.2);
            }

            .provider-card.selected {
                border-color: #3DB3E3;
                background: linear-gradient(135deg, rgba(61, 179, 227, 0.1), rgba(232, 101, 160, 0.1));
                box-shadow: 0 4px 12px rgba(61, 179, 227, 0.2);
            }

            .provider-logo {
                width: 60px;
                height: 60px;
                margin: 0 auto 16px;
                transition: transform 0.3s ease;
            }

            .provider-card:hover .provider-logo {
                transform: scale(1.1);
            }

            /* Enhanced logo bubble effect */
            .logo-hover-blink {
                transition: all 0.3s ease;
                position: relative;
                z-index: 1;
            }

            .logo-hover-blink::before {
                content: '';
                position: absolute;
                top: -10px;
                left: -10px;
                right: -10px;
                bottom: -10px;
                border-radius: 50%;
                background: radial-gradient(circle, rgba(61, 179, 227, 0.3) 0%, rgba(104, 102, 193, 0.2) 50%, rgba(232, 101, 160, 0.1) 100%);
                opacity: 0;
                transform: scale(0.8);
                transition: all 0.4s cubic-bezier(0.68, -0.55, 0.265, 1.55);
                z-index: -1;
            }

            .provider-card:hover .logo-hover-blink::before {
                opacity: 1;
                transform: scale(1.2);
                animation: bubblePulse 1.5s infinite alternate;
            }

            @keyframes bubblePulse {
                0% {
                    transform: scale(1.2);
                    box-shadow: 0 0 20px rgba(61, 179, 227, 0.3);
                }
                100% {
                    transform: scale(1.4);
                    box-shadow: 0 0 30px rgba(61, 179, 227, 0.5), 0 0 40px rgba(232, 101, 160, 0.3);
                }
            }

            /* Logo raindrop bubble effect animation */
            .logo-hover-blink::after {
                content: '';
                position: absolute;
                top: 50%;
                left: 50%;
                width: 8px;
                height: 8px;
                background: linear-gradient(135deg, rgba(61, 179, 227, 0.8) 0%, rgba(232, 101, 160, 0.6) 100%);
                border-radius: 50% 50% 50% 0%;
                transform: translate(-50%, -50%) rotate(-45deg) scale(0);
                opacity: 0;
                transition: all 0.3s ease;
                z-index: 2;
            }

            .provider-card:hover .logo-hover-blink::after {
                animation: rainDropBubble 2s infinite;
            }

            @keyframes rainDropBubble {
                0% {
                    transform: translate(-50%, -50%) rotate(-45deg) scale(0);
                    opacity: 0;
                }
                10% {
                    transform: translate(-50%, -50%) rotate(-45deg) scale(1);
                    opacity: 1;
                }
                20% {
                    transform: translate(-50%, -70%) rotate(-45deg) scale(1.2);
                    opacity: 0.8;
                }
                30% {
                    transform: translate(-50%, -90%) rotate(-45deg) scale(1.5);
                    opacity: 0.6;
                }
                40% {
                    transform: translate(-50%, -110%) rotate(-45deg) scale(1.8);
                    opacity: 0.4;
                }
                50% {
                    transform: translate(-50%, -130%) rotate(-45deg) scale(2);
                    opacity: 0.2;
                }
                60% {
                    transform: translate(-50%, -150%) rotate(-45deg) scale(2.2);
                    opacity: 0.1;
                }
                100% {
                    transform: translate(-50%, -170%) rotate(-45deg) scale(2.5);
                    opacity: 0;
                }
            }

            /* Multiple bubble drops effect */
            .logo-bubble-container {
                position: relative;
                overflow: visible;
            }

            .logo-bubble-container::before,
            .logo-bubble-container::after {
                content: '';
                position: absolute;
                width: 6px;
                height: 6px;
                background: linear-gradient(135deg, rgba(61, 179, 227, 0.7) 0%, rgba(104, 102, 193, 0.5) 50%, rgba(232, 101, 160, 0.4) 100%);
                border-radius: 50% 50% 50% 0%;
                opacity: 0;
                z-index: 2;
            }

            .logo-bubble-container::before {
                top: 20%;
                left: 30%;
                transform: rotate(-30deg);
                animation-delay: 0.5s;
            }

            .logo-bubble-container::after {
                top: 30%;
                right: 25%;
                transform: rotate(-60deg);
                animation-delay: 1s;
            }

            .provider-card:hover .logo-bubble-container::before,
            .provider-card:hover .logo-bubble-container::after {
                animation: smallBubbleDrop 1.8s infinite;
            }

            @keyframes smallBubbleDrop {
                0% {
                    transform: translateY(0) scale(0);
                    opacity: 0;
                }
                15% {
                    transform: translateY(-10px) scale(1);
                    opacity: 1;
                }
                30% {
                    transform: translateY(-25px) scale(1.2);
                    opacity: 0.8;
                }
                50% {
                    transform: translateY(-45px) scale(1.4);
                    opacity: 0.5;
                }
                70% {
                    transform: translateY(-70px) scale(1.6);
                    opacity: 0.3;
                }
                100% {
                    transform: translateY(-100px) scale(1.8);
                    opacity: 0;
                }
            }

            /* Resource row hover animations */
            .resource-row {
                transition: all 0.3s ease;
                position: relative;
                overflow: hidden;
            }

            .resource-row::before {
                content: '';
                position: absolute;
                top: 0;
                left: -100%;
                width: 100%;
                height: 100%;
                background: linear-gradient(90deg, transparent, rgba(61, 179, 227, 0.1), transparent);
                transition: left 0.5s ease;
            }

            .resource-row:hover::before {
                left: 100%;
            }

            .resource-row:hover {
                background: linear-gradient(135deg, rgba(61, 179, 227, 0.05), rgba(232, 101, 160, 0.05));
                transform: translateY(-1px);
                box-shadow: 0 2px 8px rgba(61, 179, 227, 0.1);
            }

            /* Tab hover animations with bubble effect */
            .tab-button {
                padding: 12px 20px;
                border-radius: 8px;
                transition: all 0.3s ease;
                position: relative;
                overflow: hidden;
                z-index: 1;
            }

            .tab-button.active {
                background: linear-gradient(135deg, #3DB3E3 0%, #6866C1 50%, #E865A0 100%);
                color: white;
                box-shadow: 0 4px 12px rgba(61, 179, 227, 0.3);
            }

            .tab-button.inactive {
                background: white;
                color: #64748b;
                border: 1px solid #e2e8f0;
            }

            .tab-button.inactive::before {
                content: '';
                position: absolute;
                top: 50%;
                left: 50%;
                width: 0;
                height: 0;
                background: linear-gradient(135deg, #3DB3E3 0%, #6866C1 50%, #E865A0 100%);
                border-radius: 50%;
                transition: all 0.4s ease;
                transform: translate(-50%, -50%);
                z-index: -1;
            }

            .tab-button.inactive:hover::before {
                width: 200px;
                height: 200px;
                animation: tabBubble 1s infinite alternate;
            }

            .tab-button.inactive:hover {
                color: white;
                transform: translateY(-2px);
                box-shadow: 0 6px 20px rgba(61, 179, 227, 0.2);
            }

            @keyframes tabBubble {
                0% {
                    transform: translate(-50%, -50%) scale(1);
                    box-shadow: 0 0 20px rgba(61, 179, 227, 0.3);
                }
                100% {
                    transform: translate(-50%, -50%) scale(1.1);
                    box-shadow: 0 0 30px rgba(61, 179, 227, 0.5), 0 0 40px rgba(232, 101, 160, 0.3);
                }
            }

            .provider-name {
                font-size: 16px;
                font-weight: 600;
                color: #1e293b;
            }

            .navigation {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-top: 40px;
                padding-top: 20px;
                border-top: 1px solid #e2e8f0;
            }

            /* Enhanced Animations */
            .fade-in {
                animation: fadeInUp 0.6s cubic-bezier(0.4, 0, 0.2, 1);
            }

            @keyframes fadeInUp {
                from { 
                    opacity: 0; 
                    transform: translateY(30px);
                }
                to { 
                    opacity: 1; 
                    transform: translateY(0);
                }
            }

            /* Pulse animation for loading states */
            .pulse {
                animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
            }

            @keyframes pulse {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.5; }
            }

            /* Shimmer effect */
            .shimmer {
                background: linear-gradient(90deg, #f1f5f9 25%, #e2e8f0 50%, #f1f5f9 75%);
                background-size: 200% 100%;
                animation: shimmer 2s infinite;
            }

            @keyframes shimmer {
                0% { background-position: -200% 0; }
                100% { background-position: 200% 0; }
            }

            .footer {
                background: #1e293b;
                color: white;
                text-align: center;
                padding: 40px 0;
                margin-top: 60px;
            }

            .footer-content {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 20px;
            }

            .footer-logo {
                display: flex;
                align-items: center;
                gap: 12px;
                font-size: 20px;
                font-weight: bold;
            }

            .footer-logo img {
                height: 30px;
                width: auto;
            }

            .footer-text {
                color: #94a3b8;
                font-size: 14px;
            }

            /* Responsive Design */
            @media (max-width: 768px) {
                .provider-grid {
                    grid-template-columns: 1fr;
                }

                .step-indicator {
                    gap: 10px;
                }

                .step-divider {
                    width: 30px;
                }

                .step-label {
                    display: none;
                }

                .footer-content {
                    flex-direction: column;
                    gap: 20px;
                }

                .btn {
                    padding: 12px 24px;
                    font-size: 16px;
                }
            }

            /* Report card styles */
            .report-card {
                background: white;
                border: 2px solid #e2e8f0;
                border-radius: 12px;
                padding: 24px;
                text-align: center;
                cursor: pointer;
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                background: white;
                position: relative;
                overflow: hidden;
            }

            .report-card::before {
                content: '';
                position: absolute;
                top: 0;
                left: -100%;
                width: 100%;
                height: 100%;
                background: linear-gradient(90deg, transparent, rgba(61, 179, 227, 0.1), transparent);
                transition: left 0.5s ease;
            }

            .report-card:hover::before {
                left: 100%;
            }

            .report-card:hover {
                border-color: #3DB3E3;
                transform: translateY(-4px);
                box-shadow: 0 8px 25px rgba(61, 179, 227, 0.2);
            }

            .report-card.selected {
                border-color: #3DB3E3;
                background: linear-gradient(135deg, rgba(61, 179, 227, 0.1), rgba(232, 101, 160, 0.1));
                box-shadow: 0 4px 12px rgba(61, 179, 227, 0.2);
            }

            /* Update report icons with gradient/black styling */
            .report-icon-gradient {
                background: linear-gradient(135deg, #3DB3E3 0%, #6866C1 50%, #E865A0 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
                transition: all 0.3s ease;
            }

            .report-icon-black {
                color: #1e293b;
                transition: all 0.3s ease;
            }

            .report-card:hover .report-icon-black {
                color: #000000;
                transform: scale(1.1);
            }

            .report-card:hover .report-icon-gradient {
                transform: scale(1.1);
                filter: brightness(1.2);
            }

            /* Report Card Styles */
            .report-card {
                background: white;
                border: 2px solid #e5e7eb;
                border-radius: 12px;
                padding: 2rem;
                text-align: center;
                cursor: pointer;
                transition: all 0.3s ease;
                min-height: 220px;
                display: flex;
                flex-direction: column;
                justify-content: center;
            }

            /* Frequency Card Styles */
            .frequency-card {
                background: white;
                border: 1px solid #e5e7eb;
                border-radius: 12px;
                padding: 1.5rem;
                cursor: pointer;
                transition: all 0.2s ease;
                box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
            }

            .frequency-card:hover {
                border-color: #a855f7;
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
            }

            .frequency-card.selected {
                border: 2px solid #a855f7;
                background: #faf5ff;
            }

            .frequency-card.selected i {
                color: #a855f7 !important;
            }

            /* Ensure only one frequency card can be selected */
            .frequency-card:not(.selected) i {
                color: #000000;
            }

            /* Modern Dropdown Styles */
            .client-dropdown-trigger {
                position: relative;
                cursor: pointer;
                user-select: none;
            }

            .client-dropdown-trigger:hover {
                transform: translateY(-1px);
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
                border-color: #374151;
            }

            .client-dropdown-trigger.active {
                border-color: #000000;
                box-shadow: 0 0 0 3px rgba(0, 0, 0, 0.1);
            }

            .client-dropdown-trigger.active #client-dropdown-arrow {
                transform: rotate(180deg);
                color: #000000;
            }

            .client-dropdown-menu {
                backdrop-filter: blur(10px);
                border: 2px solid rgba(0, 0, 0, 0.2);
                max-height: 400px;
            }

            .client-dropdown-menu.show {
                opacity: 1;
                visibility: visible;
                transform: translateY(0);
                animation: dropdownSlideIn 0.3s ease-out;
            }

            @keyframes dropdownSlideIn {
                0% {
                    opacity: 0;
                    transform: translateY(-10px) scale(0.95);
                }
                100% {
                    opacity: 1;
                    transform: translateY(0) scale(1);
                }
            }

            .client-option {
                padding: 12px 16px;
                cursor: pointer;
                transition: all 0.2s ease;
                border-left: 3px solid transparent;
                position: relative;
                overflow: hidden;
            }

            .client-option::before {
                content: '';
                position: absolute;
                top: 0;
                left: -100%;
                width: 100%;
                height: 100%;
                background: linear-gradient(90deg, transparent, rgba(248, 250, 252, 0.5), transparent);
                transition: left 0.5s ease;
            }

            .client-option:hover::before {
                left: 100%;
            }

            .client-option:hover {
                background: #f8fafc;
                border-left-color: transparent;
                transform: translateX(4px);
                color: #1e293b;
            }

            .client-option.selected {
                background: white;
                color: #1e293b;
                border: none !important;
                border-left: none !important;
                font-weight: 600;
            }

            .client-option.selected::after {
                content: '✓';
                position: absolute;
                right: 16px;
                top: 50%;
                transform: translateY(-50%);
                font-weight: bold;
            }

            /* Custom Scrollbar for Client List */
            .client-list::-webkit-scrollbar {
                width: 6px;
            }

            .client-list::-webkit-scrollbar-track {
                background: #f1f5f9;
                border-radius: 3px;
            }

            .client-list::-webkit-scrollbar-thumb {
                background: #e2e8f0;
                border-radius: 3px;
                transition: background 0.3s ease;
            }```tool_code
            .client-list::-webkit-scrollbar-thumb:hover {
                background: #cbd5e1;
            }

            /* Search Input Styling */
            #client-search {
                font-size: 14px;
            }

            #client-search:focus {
                outline: none;
                box-shadow: 0 0 0 3px rgba(0, 0, 0, 0.1);
            }

            /* Loading Animation */
            .client-option-loading {
                animation: clientOptionFadeIn 0.4s ease-out;
            }

            @keyframes clientOptionFadeIn {
                0% {
                    opacity: 0;
                    transform: translateY(10px);
                }
                100% {
                    opacity: 1;
                    transform: translateY(0);
                }
            }

            /* Accessibility improvements */
            @media (prefers-reduced-motion: reduce) {
                * {
                    animation-duration: 0.01ms !important;
                    animation-iteration-count: 1 !important;
                    transition-duration: 0.01ms !important;
                }
            }
        </style>
    </head>
    <body class="bg-gray-50 min-h-screen">
        <div id="app">
            <!-- Header -->
            <header class="bg-white shadow-sm border-b sticky top-0 z-50 w-full">
                <div class="w-full px-4 sm:px-6 lg:px-8 py-4">
                    <div class="flex items-center justify-between">
                        <div class="flex items-center space-x-3">
                            <img src="/static/nubinix-logo.png" alt="Nubinix" class="h-10 w-10">
                            <h1 class="text-2xl font-bold bg-gradient-to-r from-[#3DB3E3] via-[#6866C1] to-[#E865A0] bg-clip-text text-transparent drop-shadow-md">
                                Cloud Insights
                            </h1>
                        </div>
                        <div class="text-sm font-medium bg-gradient-to-r from-[#3DB3E3] via-[#6866C1] to-[#E865A0] bg-clip-text text-transparent drop-shadow-md">
                            <a href="https://www.nubinix.com" target="_blank" rel="noopener noreferrer">www.nubinix.com</a>
                        </div>
                    </div>
                </div>
            </header>

            <!-- Main Content -->
            <main class="w-full px-4 sm:px-6 lg:px-8 py-8">
                <!-- Step Progress Indicator -->
                <div class="mb-8">
                    <div class="flex items-center justify-center space-x-8 max-w-4xl mx-auto">
                        <!-- Step 1 -->
                        <div class="flex flex-col items-center">
                            <div id="step1" class="step-active flex items-center justify-center w-12 h-12 rounded-full font-bold text-lg transition-all duration-300">1</div>
                            <span class="text-sm text-gray-600 mt-3 font-medium">Provider</span>
                        </div>

                        <!-- Line 1 -->
                        <div class="w-16 h-0.5 bg-gray-300 rounded transition-all duration-300 mt-[-20px]" id="line1"></div>

                        <!-- Step 2 -->
                        <div class="flex flex-col items-center">
                            <div id="step2" class="step-inactive flex items-center justify-center w-12 h-12 rounded-full font-bold text-lg transition-all duration-300">2</div>
                            <span class="text-sm text-gray-600 mt-3 font-medium">Client</span>
                        </div>

                        <!-- Line 2 -->
                        <div class="w-16 h-0.5 bg-gray-300 rounded transition-all duration-300 mt-[-20px]" id="line2"></div>

                        <!-- Step 3 -->
                        <div class="flex flex-col items-center">
                            <div id="step3" class="step-inactive flex items-center justify-center w-12 h-12 rounded-full font-bold text-lg transition-all duration-300">3</div>
                            <span class="text-sm text-gray-600 mt-3 font-medium">Report</span>
                        </div>

                        <!-- Line 3 -->
                        <div class="w-16 h-0.5 bg-gray-300 rounded transition-all duration-300 mt-[-20px]" id="line3"></div>

                        <!-- Step 4 -->
                        <div class="flex flex-col items-center">
                            <div id="step4" class="step-inactive flex items-center justify-center w-12 h-12 rounded-full font-bold text-lg transition-all duration-300">4</div>
                            <span class="text-sm text-gray-600 mt-3 font-medium">Config</span>
                        </div>

                        <!-- Line 4 -->
                        <div class="w-16 h-0.5 bg-gray-300 rounded transition-all duration-300 mt-[-20px]" id="line4"></div>

                        <!-- Step 5 -->
                        <div class="flex flex-col items-center">
                            <div id="step5" class="step-inactive flex items-center justify-center w-12 h-12 rounded-full font-bold text-lg transition-all duration-300">5</div>
                            <span class="text-sm text-gray-600 mt-3 font-medium">Generate</span>
                        </div>
                    </div>
                </div>

                <!-- Step Content Container -->
                <div class="bg-white rounded-2xl shadow-lg p-8 border border-gray-300">

                    <!-- Step 1: Cloud Provider Selection -->
                    <div id="step1-content" class="fade-in">
                        <div class="text-center mb-8">
                            <h2 class="text-3xl font-bold text-gray-900 mb-4">Select Cloud Provider</h2>
                            <p class="text-gray-600 text-lg">Choose your cloud platform to begin analysis</p>
                        </div>
                        <div class="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-4xl mx-auto">
                            <div class="provider-card" id="aws-card" onclick="selectProvider('AWS')">
                                <div class="flex items-center justify-center mb-4 logo-bubble-container">
                                    <img src="/static/aws.svg" alt="AWS" class="h-16 w-16 logo-hover-blink">
                                </div>
                                <p class="text-gray-600 text-center">Amazon Web Services</p>
                                <div class="flex justify-center mt-4">
                                    <div class="hidden" id="aws-check">
                                        <i data-lucide="check-circle" class="text-[#3DB3E3] h-8 w-8"></i>
                                    </div>
                                </div>
                            </div>
                            <div class="provider-card" id="azure-card" onclick="selectProvider('Azure')">
                                <div class="flex items-center justify-center mb-4 logo-bubble-container">
                                    <img src="/static/azure.svg" alt="Azure" class="h-16 w-16 logo-hover-blink">
                                </div>
                                <p class="text-gray-600 text-center">Microsoft Azure</p>
                                <div class="flex justify-center mt-4">
                                    <div class="hidden" id="azure-check">
                                        <i data-lucide="check-circle" class="text-[#3DB3E3] h-8 w-8"></i>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Step 2: Client Selection -->
                    <div id="step2-content" class="hidden fade-in">
                        <div class="text-center mb-8">
                            <h2 class="text-3xl font-bold text-gray-900 mb-4">Select Nubinix Client</h2>
                            <p class="text-gray-600 text-lg">Choose the client account for analysis</p>
                        </div>
                        <div class="max-w-2xl mx-auto">
                            <div class="mb-6">
                                <label class="block text-lg font-medium text-gray-700 mb-3">Client Account</label>

                                <!-- Custom Dropdown -->
                                <div class="relative">
                                    <button type="button" id="client-dropdown-btn" onclick="toggleClientDropdown()" 
                                            class="client-dropdown-trigger w-full p-4 text-lg border-2 border-gray-300 rounded-xl bg-white text-left flex items-center justify-between transition-all duration-300 hover:border-blue-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-200">
                                        <span id="client-dropdown-text" class="text-gray-500">Loading clients...</span>
                                        <i data-lucide="chevron-down" id="client-dropdown-arrow" class="h-5 w-5 text-gray-400 transition-transform duration-300"></i>
                                    </button>

                                    <!-- Dropdown Menu -->
                                    <div id="client-dropdown-menu" class="client-dropdown-menu absolute top-full left-0 right-0 mt-2 bg-white border-2 border-gray-200 rounded-xl shadow-xl z-50 opacity-0 invisible transform translate-y-[-10px] transition-all duration-300">
                                        <!-- Search Box -->
                                        <div class="p-3 border-b border-gray-200">
                                            <div class="relative">
                                                <i data-lucide="search" class="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400"></i>
                                                <input type="text" id="client-search" placeholder="Search clients..." 
                                                       class="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-200 focus:border-blue-500 transition-colors"
                                                       onkeyup="filterClients()">
                                            </div>
                                        </div>

                                        <!-- Client List with Scroll -->
                                        <div class="client-list max-h-60 overflow-y-auto">
                                            <div id="client-dropdown-loading" class="p-4 text-center text-gray-500">
                                                <i data-lucide="loader-2" class="h-5 w-5 animate-spin mx-auto mb-2"></i>
                                                Loading clients...
                                            </div>
                                            <div id="client-dropdown-options" class="hidden"></div>
                                            <div id="client-dropdown-empty" class="hidden p-4 text-center text-gray-500">
                                                <i data-lucide="search-x" class="h-5 w-5 mx-auto mb-2 text-gray-400"></i>
                                                No clients found
                                            </div>
                                        </div>
                                    </div>
                                </div>

                                <!-- Hidden input for form submission -->
                                <input type="hidden" id="client-select" value="">
                            </div>

                        </div>
                    </div>

                    <!-- Step 3: Report Type Selection -->
                    <div id="step3-content" class="hidden fade-in">
                        <div class="text-center mb-8">
                            <h2 class="text-3xl font-bold text-gray-900 mb-4">Select Report Type</h2>
                            <p class="text-gray-600 text-lg">Choose the type of analysis you need</p>
                        </div>
                        <div class="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-4xl mx-auto">
                            <div class="report-card" id="utilization-card" onclick="selectReportType('utilization')">
                                <div class="flex items-center justify-center mb-4">
                                    <i data-lucide="activity" class="h-16 w-16 report-icon-gradient"></i>
                                </div>
                                <h3 class="text-2xl font-bold text-center mb-2">Utilization Report</h3>
                                <p class="text-gray-600 text-center">Resource usage and performance metrics</p>
                                <div class="flex justify-center mt-4">
                                    <div class="hidden" id="utilization-check">
                                        <i data-lucide="check-circle" class="text-[#3DB3E3] h-8 w-8"></i>
                                    </div>
                                </div>
                            </div>
                            <div class="report-card" id="billing-card" onclick="selectReportType('billing')">
                                <div class="flex items-center justify-center mb-4">
                                    <i data-lucide="dollar-sign" class="h-16 w-16 report-icon-black"></i>
                                </div>
                                <h3 class="text-2xl font-bold text-center mb-2">Billing Report</h3>
                                <p class="text-gray-600 text-center">Cost analysis and billing breakdown</p>
                                <div class="flex justify-center mt-4">
                                    <div class="hidden" id="billing-check">
                                        <i data-lucide="check-circle" class="text-[#3DB3E3] h-8 w-8"></i>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Step 4A: Utilization - Resource Selection -->
                    <div id="step4a-content" class="hidden fade-in">
                        <div class="text-center mb-8">
                            <h2 class="text-3xl font-bold text-gray-900 mb-4">Select Resources</h2>
                            <p class="text-gray-600 text-lg">Choose the resources you want to analyze</p>
                        </div>

                        <div class="mb-8">
                            <div class="flex space-x-2 bg-gray-100 p-2 rounded-xl max-w-md mx-auto">
                                <button id="ec2-tab" class="tab-button active flex-1" onclick="switchResourceTab('ec2')">
                                    <i data-lucide="server" class="inline h-5 w-5 mr-2"></i>
                                    EC2 Instances
                                </button>
                                <button id="rds-tab" class="tab-button inactive flex-1" onclick="switchResourceTab('rds')">
                                    <i data-lucide="database" class="inline h-5 w-5 mr-2"></i>
                                    RDS Instances
                                </button>
                            </div>
                        </div>

                        <!-- Resource Tables -->
                        <div id="ec2-resources" class="resource-tab-content">
                            <div class="text-center mb-6">
                                <button onclick="scanResources('EC2')" class="bg-gradient-to-r from-green-500 to-emerald-500 text-white px-6 py-3 rounded-xl font-medium hover:from-green-600 hover:to-emerald-600 transform hover:scale-105 transition-all duration-200 shadow-lg">
                                    <i data-lucide="search" class="inline h-5 w-5 mr-2"></i>
                                    Scan EC2 Instances
                                </button>
                            </div>
                            <div id="ec2-table" class="hidden resource-table">
                                <div class="bg-gray-50 px-6 py-4 border-b">
                                    <div class="grid grid-cols-12 gap-4 text-sm font-semibold text-gray-700">
                                        <div class="col-span-1">
                                            <input type="checkbox" id="ec2-select-all" onchange="toggleSelectAll('ec2')" class="rounded border-gray-300">
                                        </div>
                                        <div class="col-span-3">Instance ID</div>
                                        <div class="col-span-3">Name</div>
                                        <div class="col-span-2">Type</div>
                                        <div class="col-span-2">State</div>
                                        <div class="col-span-1">Region</div>
                                    </div>
                                </div>
                                <div id="ec2-tbody" class="divide-y divide-gray-200"></div>
                            </div>
                        </div>

                        <div id="rds-resources" class="resource-tab-content hidden">
                            <div class="text-center mb-6">
                                <button onclick="scanResources('RDS')" class="bg-gradient-to-r from-green-500 to-emerald-500 text-white px-6 py-3 rounded-xl font-medium hover:from-green-600 hover:to-emerald-600 transform hover:scale-105 transition-all duration-200 shadow-lg">
                                    <i data-lucide="search" class="inline h-5 w-5 mr-2"></i>
                                    Scan RDS Instances
                                </button>
                            </div>
                            <div id="rds-table" class="hidden resource-table">
                                <div class="bg-gray-50 px-6 py-4 border-b">
                                    <div class="grid grid-cols-12 gap-4 text-sm font-semibold text-gray-700">
                                        <div class="col-span-1">
                                            <input type="checkbox" id="rds-select-all" onchange="toggleSelectAll('rds')" class="rounded border-gray-300">
                                        </div>
                                        <div class="col-span-3">Instance ID</div>
                                        <div class="col-span-3">Name</div>
                                        <div class="col-span-2">Type</div>
                                        <div class="col-span-2">Status</div>
                                        <div class="col-span-1">Region</div>
                                    </div>
                                </div>
                                <div id="rds-tbody" class="divide-y divide-gray-200"></div>
                            </div>
                        </div>


                    </div>

                    <!-- Step 4B: Billing - Period Selection -->
                    <div id="step4b-content" class="hidden fade-in">
                        <div class="text-center mb-8">
                            <h2 class="text-3xl font-bold text-gray-900 mb-4">Select Billing Period</h2>
                            <p class="text-gray-600 text-lg">Choose the month and year for billing analysis</p>
                        </div>
                        <div class="max-w-2xl mx-auto">
                            <div class="grid grid-cols-2 gap-6 mb-8">
                                <div>
                                    <label class="block text-lg font-medium text-gray-700 mb-3">Month</label>
                                    <select id="month-select" onchange="updateNavigationButtons()" class="w-full p-4 text-lg border-2 border-gray-300 rounded-xl focus:ring-blue-500 focus:border-blue-500">
                                        <option value="1">January</option>
                                        <option value="2">February</option>
                                        <option value="3">March</option>
                                        <option value="4">April</option>
                                        <option value="5">May</option>
                                        <option value="6">June</option>
                                        <option value="7">July</option>
                                        <option value="8">August</option>
                                        <option value="9">September</option>
                                        <option value="10">October</option>
                                        <option value="11">November</option>
                                        <option value="12">December</option>
                                    </select>
                                </div>
                                <div>
                                    <label class="block text-lg font-medium text-gray-700 mb-3">Year</label>
                                    <select id="year-select" onchange="updateNavigationButtons()" class="w-full p-4 text-lg border-2 border-gray-300 rounded-xl focus:ring-blue-500 focus:border-blue-500">
                                        <option value="2025">2025</option>
                                        <option value="2024">2024</option>
                                        <option value="2023">2023</option>
                                        <option value="2022">2022</option>
                                    </select>
                                </div>
                            </div>

                        </div>
                    </div>



                    <!-- Step 5A: Utilization - Frequency Selection -->
                    <div id="step5a-content" class="hidden fade-in">
                        <div class="text-center mb-8">
                            <h2 class="text-3xl font-bold text-gray-900 mb-4">Select Frequency</h2>
                            <p class="text-gray-600 text-lg">Choose the reporting frequency</p>
                        </div>
                        <div class="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-4xl mx-auto mb-8">
                            <div class="report-card" id="daily-card" onclick="selectFrequency('daily')">
                                <div class="flex items-center justify-center mb-4">
                                    <i data-lucide="calendar" class="h-16 w-16 report-icon-gradient"></i>
                                </div>
                                <h3 class="text-2xl font-bold text-center mb-2">Daily</h3>
                                <p class="text-gray-600 text-center">Last 24 hours</p>
                                <div class="flex justify-center mt-4">
                                    <div class="hidden" id="daily-check">
                                        <i data-lucide="check-circle" class="text-[#3DB3E3] h-8 w-8"></i>
                                    </div>
                                </div>
                            </div>
                            <div class="report-card" id="weekly-card" onclick="selectFrequency('weekly')">
                                <div class="flex items-center justify-center mb-4">
                                    <i data-lucide="calendar-days" class="h-16 w-16 report-icon-black"></i>
                                </div>
                                <h3 class="text-2xl font-bold text-center mb-2">Weekly</h3>
                                <p class="text-gray-600 text-center">Last 7 days</p>
                                <div class="flex justify-center mt-4">
                                    <div class="hidden" id="weekly-check">
                                        <i data-lucide="check-circle" class="text-[#3DB3E3] h-8 w-8"></i>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- Download Button -->
                        <div class="text-center">
                            <button id="download-utilization-btn" onclick="downloadUtilizationReport()" class="hidden button-black-bubble text-white px-8 py-4 rounded-xl font-medium text-lg transition-all duration-200 shadow-lg">
                                <i data-lucide="download" class="inline h-5 w-5 mr-2"></i>
                                Download PDF Report
                            </button>
                        </div>
                    </div>

                    <!-- Step 5B: Billing Data Display -->
                    <div id="step5b-content" class="hidden fade-in">
                        <div class="text-center mb-8">
                            <h2 class="text-3xl font-bold text-gray-900 mb-4">Billing Analysis</h2>
                            <p class="text-gray-600 text-lg">Review your billing information and trends</p>
                        </div>
                        <div id="billing-data-container" class="max-w-6xl mx-auto">
                            <div class="text-center text-gray-500">
                                <i data-lucide="loader-2" class="h-8 w-8 animate-spin mx-auto mb-4"></i>
                                Loading billing data...
                            </div>
                        </div>
                        <div class="text-center mt-8">
                            <button onclick="downloadBillingReport()" class="button-black-bubble text-white px-8 py-4 rounded-xl font-medium text-lg transition-all duration-200 shadow-lg">
                                <i data-lucide="download" class="inline h-5 w-5 mr-2"></i>
                                Download PDF Report
                            </button>
                        </div>
                    </div>

                    <!-- Navigation Buttons -->
                    <div class="flex justify-center space-x-4 mt-8 pt-6 border-t border-gray-200">
                        <button id="back-btn" onclick="goBack()" class="hidden btn btn-outline">
                            <i data-lucide="arrow-left" class="inline h-5 w-5 mr-2"></i>
                            Back
                        </button>
                        <button id="next-btn" onclick="goNext()" class="hidden btn btn-primary">
                            Next
                            <i data-lucide="arrow-right" class="inline h-5 w-5 ml-2"></i>
                        </button>
                    </div>
                </div>
            </main>

            <!-- Footer -->
            <footer class="border-t py-4 px-6 bg-gradient-to-t from-black to-transparent mt-4 w-full">
                <div class="w-full flex flex-col sm:flex-row justify-between items-center gap-4">
                    <div class="flex items-center gap-2">
                        <img src="/static/nubinix-logo.png" alt="Nubinix" class="h-6 w-6">
                        <span class="text-sm text-white">
                            © 2025 Nubinix. All rights reserved.
                        </span>
                    </div>
                    <div class="flex gap-6">
                        <a
                            href="https://nubinix.com/privacy-policy/"
                            target="_blank"
                            rel="noopener noreferrer"
                            class="text-sm text-white hover:text-gray-300 transition-colors"
                        >
                            Privacy Policy
                        </a>
                        <a
                            href="https://nubinix.com/terms-of-use/"
                            target="_blank"
                            rel="noopener noreferrer"
                            class="text-sm text-white hover:text-gray-300 transition-colors"
                        >
                            Terms of Service
                        </a>
                        <a
                            href="https://nubinix.com/contact-us/"
                            target="_blank"
                            rel="noopener noreferrer"
                            class="text-sm text-white hover:text-gray-300 transition-colors"
                        >
                            Contact Us
                        </a>
                    </div>
                </div>
            </footer>
        </div>

        <script>
            // Initialize Lucide icons
            lucide.createIcons();

            // Application state
            let currentStep = 1;
            let selectedProvider = '';
            let selectedClient = '';
            let selectedReportType = '';
            let selectedResources = [];
            let selectedFrequency = '';
            let clientCredentials = null;
            let ec2Resources = [];
            let rdsResources = [];

            function updateStepIndicator() {
                for (let i = 1; i <= 5; i++) {
                    const step = document.getElementById('step' + i);
                    const line = document.getElementById('line' + i);

                    if (i < currentStep) {
                        step.className = 'step-completed flex items-center justify-center w-12 h-12 rounded-full font-bold text-lg transition-all duration-300';
                        if (line) line.className = 'w-16 h-0.5 bg-green-400 rounded transition-all duration-300 mt-[-20px]';
                    } else if (i === currentStep) {
                        step.className = 'step-active flex items-center justify-center w-12 h-12 rounded-full font-bold text-lg transition-all duration-300';
                    } else {
                        step.className = 'step-inactive flex items-center justify-center w-12 h-12 rounded-full font-bold text-lg transition-all duration-300';
                        if (line) line.className = 'w-16 h-0.5 bg-gray-300 rounded transition-all duration-300 mt-[-20px]';
                    }
                }

                updateNavigationButtons();
            }

            function updateNavigationButtons() {
                const backBtn = document.getElementById('back-btn');
                const nextBtn = document.getElementById('next-btn');

                // Show back button for all steps except step 1
                if (currentStep > 1) {
                    backBtn.classList.remove('hidden');
                } else {
                    backBtn.classList.add('hidden');
                }

                // Show next button based on current step and selections
                let showNext = false;

                if (currentStep === 1 && selectedProvider) {
                    showNext = true;
                } else if (currentStep === 2 && selectedClient) {
                    showNext = true;
                } else if (currentStep === 3 && selectedReportType) {
                    showNext = true;
                } else if (currentStep === 4) {
                    if (selectedReportType === 'utilization' && selectedResources.length > 0) {
                        showNext = true;
                    } else if (selectedReportType === 'billing') {
                        const month = document.getElementById('month-select').value;
                        const year = document.getElementById('year-select').value;
                        if (month && year) {
                            showNext = true;
                        }
                    }
                }

                if (showNext) {
                    nextBtn.classList.remove('hidden');
                } else {
                    nextBtn.classList.add('hidden');
                }
            }

            function goBack() {
                if (currentStep > 1) {
                    currentStep--;
                    
                    // Handle special step transitions when going back
                    if (currentStep === 4) {
                        // Going back to step 4, show appropriate content based on report type
                        if (selectedReportType === 'utilization') {
                            document.getElementById('step5a-content')?.classList.add('hidden');
                            document.getElementById('step4a-content')?.classList.remove('hidden');
                            document.getElementById('step4a-content')?.classList.add('fade-in');
                        } else if (selectedReportType === 'billing') {
                            document.getElementById('step5b-content')?.classList.add('hidden');
                            document.getElementById('step4b-content')?.classList.remove('hidden');
                            document.getElementById('step4b-content')?.classList.add('fade-in');
                        }
                        updateStepIndicator();
                        lucide.createIcons();
                    } else {
                        // For other steps, use regular showStep function
                        showStep(currentStep);
                    }
                }
            }

            function goNext() {
                if (currentStep === 1 && selectedProvider) {
                    currentStep = 2;
                    showStep(2);
                    loadClients();
                } else if (currentStep === 2 && selectedClient) {
                    currentStep = 3;
                    showStep(3);
                } else if (currentStep === 3 && selectedReportType) {
                    currentStep = 4;
                    if (selectedReportType === 'utilization') {
                        document.getElementById('step3-content').classList.add('hidden');
                        document.getElementById('step4a-content').classList.remove('hidden');
                        document.getElementById('step4a-content').classList.add('fade-in');
                        autoScanAllResources();
                    } else {
                        document.getElementById('step3-content').classList.add('hidden');
                        document.getElementById('step4b-content').classList.remove('hidden');
                        document.getElementById('step4b-content').classList.add('fade-in');
                    }
                    updateStepIndicator();
                    lucide.createIcons();
                } else if (currentStep === 4) {
                    if (selectedReportType === 'utilization' && selectedResources.length > 0) {
                        currentStep = 5;
                        document.getElementById('step4a-content').classList.add('hidden');
                        document.getElementById('step5a-content').classList.remove('hidden');
                        document.getElementById('step5a-content').classList.add('fade-in');
                        updateStepIndicator();
                        lucide.createIcons();
                    } else if (selectedReportType === 'billing') {
                        const month = document.getElementById('month-select').value;
                        const year = document.getElementById('year-select').value;
                        if (month && year) {
                            currentStep = 5;
                            document.getElementById('step4b-content').classList.add('hidden');
                            document.getElementById('step5b-content').classList.remove('hidden');
                            document.getElementById('step5b-content').classList.add('fade-in');
                            updateStepIndicator();
                            lucide.createIcons();
                            showBillingData(month, year, 'monthly');
                        }
                    }
                }
            }

            function showStep(step) {
                // Hide all steps
                for (let i = 1; i <= 5; i++) {
                    const stepContent = document.getElementById('step' + i + '-content');
                    if (stepContent) stepContent.classList.add('hidden');
                }
                document.getElementById('step4a-content')?.classList.add('hidden');
                document.getElementById('step4b-content')?.classList.add('hidden');
                document.getElementById('step5a-content')?.classList.add('hidden');
                document.getElementById('step5b-content')?.classList.add('hidden');

                // Show appropriate step content based on current step and selections
                if (step === 4 && selectedReportType === 'utilization') {
                    document.getElementById('step4a-content')?.classList.remove('hidden');
                    document.getElementById('step4a-content')?.classList.add('fade-in');
                } else if (step === 4 && selectedReportType === 'billing') {
                    document.getElementById('step4b-content')?.classList.remove('hidden');
                    document.getElementById('step4b-content')?.classList.add('fade-in');
                } else if (step === 5 && selectedReportType === 'utilization') {
                    document.getElementById('step5a-content')?.classList.remove('hidden');
                    document.getElementById('step5a-content')?.classList.add('fade-in');
                } else if (step === 5 && selectedReportType === 'billing') {
                    document.getElementById('step5b-content')?.classList.remove('hidden');
                    document.getElementById('step5b-content')?.classList.add('fade-in');
                } else {
                    // Show regular step content for steps 1, 2, 3
                    const currentStepContent = document.getElementById('step' + step + '-content');
                    if (currentStepContent) {
                        currentStepContent.classList.remove('hidden');
                        currentStepContent.classList.add('fade-in');
                    }
                }

                updateStepIndicator();
                lucide.createIcons(); // Reinitialize icons
            }

            function selectProvider(provider) {
                selectedProvider = provider;

                // Update UI - Remove selected state from all cards and hide all checkmarks
                document.querySelectorAll('.provider-card').forEach(function(card) {
                    card.classList.remove('selected');
                });
                document.querySelectorAll('[id$="-check"]').forEach(function(check) {
                    check.classList.add('hidden');
                });

                // Add selected state to clicked card and show its checkmark
                document.getElementById(provider.toLowerCase() + '-card').classList.add('selected');
                document.getElementById(provider.toLowerCase() + '-check').classList.remove('hidden');

                // Show next button
                updateNavigationButtons();
            }

            let clientsData = [];
            let isDropdownOpen = false;

            async function loadClients() {
                try {
                    const response = await fetch('/api/nubinix-clients');
                    const data = await response.json();

                    const loadingDiv = document.getElementById('client-dropdown-loading');
                    const optionsDiv = document.getElementById('client-dropdown-options');
                    const dropdownText = document.getElementById('client-dropdown-text');

                    if (data.success) {
                        clientsData = data.clients;
                        populateClientDropdown(clientsData);

                        // Update dropdown trigger text
                        dropdownText.textContent = 'Select a client...';
                        dropdownText.classList.remove('text-gray-500');
                        dropdownText.classList.add('text-gray-700');

                        // Hide loading and show options
                        loadingDiv.classList.add('hidden');
                        optionsDiv.classList.remove('hidden');
                    } else {
                        dropdownText.textContent = 'Error loading clients';
                        loadingDiv.classList.add('hidden');
                    }
                } catch (error) {
                    console.error('Error loading clients:', error);
                    document.getElementById('client-dropdown-text').textContent = 'Error loading clients';
                    document.getElementById('client-dropdown-loading').classList.add('hidden');
                }
            }

            function populateClientDropdown(clients) {
                const optionsDiv = document.getElementById('client-dropdown-options');
                optionsDiv.innerHTML = '';

                clients.forEach((client, index) => {
                    const option = document.createElement('div');
                    option.className = 'client-option client-option-loading';
                    option.style.animationDelay = `${index * 0.05}s`;
                    option.textContent = client.charAt(0).toUpperCase() + client.slice(1);
                    option.onclick = () => selectClient(client, option);
                    optionsDiv.appendChild(option);
                });
            }

            function toggleClientDropdown() {
                const menu = document.getElementById('client-dropdown-menu');
                const trigger = document.getElementById('client-dropdown-btn');

                isDropdownOpen = !isDropdownOpen;

                if (isDropdownOpen) {
                    menu.classList.add('show');
                    trigger.classList.add('active');

                    // Focus search input when opened
                    setTimeout(() => {
                        document.getElementById('client-search').focus();
                    }, 100);

                    // Add click outside listener
                    setTimeout(() => {
                        document.addEventListener('click', closeDropdownOnClickOutside);
                    }, 100);
                } else {
                    menu.classList.remove('show');
                    trigger.classList.remove('active');
                    document.removeEventListener('click', closeDropdownOnClickOutside);
                }

                lucide.createIcons();
            }

            function closeDropdownOnClickOutside(event) {
                const dropdown = document.getElementById('client-dropdown-menu');
                const trigger = document.getElementById('client-dropdown-btn');

                if (!dropdown.contains(event.target) && !trigger.contains(event.target)) {
                    closeClientDropdown();
                }
            }

            function closeClientDropdown() {
                const menu = document.getElementById('client-dropdown-menu');
                const trigger = document.getElementById('client-dropdown-btn');

                isDropdownOpen = false;
                menu.classList.remove('show');
                trigger.classList.remove('active');
                document.removeEventListener('click', closeDropdownOnClickOutside);

                // Clear search
                document.getElementById('client-search').value = '';
                populateClientDropdown(clientsData);
            }

            function selectClient(clientValue, optionElement) {
                selectedClient = clientValue;

                // Update hidden input
                document.getElementById('client-select').value = clientValue;

                // Update dropdown text
                const dropdownText = document.getElementById('client-dropdown-text');
                dropdownText.textContent = clientValue.charAt(0).toUpperCase() + clientValue.slice(1);
                dropdownText.classList.remove('text-gray-500');
                dropdownText.classList.add('text-gray-900');

                // Update visual selection
                document.querySelectorAll('.client-option').forEach(opt => {
                    opt.classList.remove('selected');
                });
                optionElement.classList.add('selected');

                // Close dropdown with animation
                setTimeout(() => {
                    closeClientDropdown();
                    updateNavigationButtons();
                }, 200);
            }

            function filterClients() {
                const searchTerm = document.getElementById('client-search').value.toLowerCase();
                const filteredClients = clientsData.filter(client => 
                    client.toLowerCase().includes(searchTerm)
                );

                const optionsDiv = document.getElementById('client-dropdown-options');
                const emptyDiv = document.getElementById('client-dropdown-empty');

                if (filteredClients.length > 0) {
                    populateClientDropdown(filteredClients);
                    optionsDiv.classList.remove('hidden');
                    emptyDiv.classList.add('hidden');
                } else {
                    optionsDiv.classList.add('hidden');
                    emptyDiv.classList.remove('hidden');
                }

                lucide.createIcons();
            }

            function proceedToStep3() {
                selectedClient = document.getElementById('client-select').value;
                updateNavigationButtons();
            }

            function selectReportType(type) {
                selectedReportType = type;

                // Update UI - Remove selected state from all cards and hide all checkmarks
                document.querySelectorAll('.report-card').forEach(function(card) {
                    card.classList.remove('selected');
                });
                document.querySelectorAll('[id$="-check"]').forEach(function(check) {
                    check.classList.add('hidden');
                });

                // Add selected state to clicked card and show its checkmark
                document.getElementById(type + '-card').classList.add('selected');
                document.getElementById(type + '-check').classList.remove('hidden');

                // Show next button
                updateNavigationButtons();
            }

            function switchResourceTab(tabName) {
                // Update tab buttons
                document.getElementById('ec2-tab').className = tabName === 'ec2' ? 'tab-button active flex-1' : 'tab-button inactive flex-1';
                document.getElementById('rds-tab').className = tabName === 'rds' ? 'tab-button active flex-1' : 'tab-button inactive flex-1';

                // Update content
                document.getElementById('ec2-resources').classList.toggle('hidden', tabName !== 'ec2');
                document.getElementById('rds-resources').classList.toggle('hidden', tabName !== 'rds');

                lucide.createIcons();
            }

            async function autoScanAllResources() {
                try {
                    // Show loading state for both scan buttons
                    const ec2Button = document.querySelector('#ec2-resources button');
                    const rdsButton = document.querySelector('#rds-resources button');

                    if (ec2Button) {
                        ec2Button.innerHTML = '<i data-lucide="loader-2" class="inline h-5 w-5 mr-2 animate-spin"></i>Scanning EC2...';
                        ec2Button.disabled = true;
                    }
                    if (rdsButton) {
                        rdsButton.innerHTML = '<i data-lucide="loader-2" class="inline h-5 w-5 mr-2 animate-spin"></i>Scanning RDS...';
                        rdsButton.disabled = true;
                    }

                    lucide.createIcons();

                    const response = await fetch('/api/discover-resources', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            cloudProvider: selectedProvider,
                            clientName: selectedClient
                        })
                    });

                    const data = await response.json();

                    if (data.success) {
                        // Filter and display EC2 resources
                        ec2Resources = data.resources.filter(r => r.service_type === 'EC2');
                        displayResources('ec2', ec2Resources);

                        // Filter and display RDS resources
                        rdsResources = data.resources.filter(r => r.service_type === 'RDS');
                        displayResources('rds', rdsResources);

                        // Update button text to show completion
                        if (ec2Button) {
                            ec2Button.innerHTML = '<i data-lucide="check-circle" class="inline h-5 w-5 mr-2"></i>EC2 Scanned (' + ec2Resources.length + ')';
                            ec2Button.disabled = false;
                            ec2Button.classList.add('bg-green-500', 'hover:bg-green-600');
                            ec2Button.classList.remove('bg-gradient-to-r', 'from-green-500', 'to-emerald-500', 'hover:from-green-600', 'hover:to-emerald-600');
                        }

                        if (rdsButton) {
                            rdsButton.innerHTML = '<i data-lucide="check-circle" class="inline h-5 w-5 mr-2"></i>RDS Scanned (' + rdsResources.length + ')';
                            rdsButton.disabled = false;
                            rdsButton.classList.add('bg-green-500', 'hover:bg-green-600');
                            rdsButton.classList.remove('bg-gradient-to-r', 'from-green-500', 'to-emerald-500', 'hover:from-green-600', 'hover:to-emerald-600');
                        }

                        lucide.createIcons();
                    }
                } catch (error) {
                    console.error('Error auto-scanning resources:', error);

                    // Reset buttons on error
                    if (ec2Button) {
                        ec2Button.innerHTML = '<i data-lucide="search" class="inline h-5 w-5 mr-2"></i>Scan EC2 Instances';
                        ec2Button.disabled = false;
                    }
                    if (rdsButton) {
                        rdsButton.innerHTML = '<i data-lucide="search" class="inline h-5 w-5 mr-2"></i>Scan RDS Instances';
                        rdsButton.disabled = false;
                    }
                    lucide.createIcons();
                }
            }

            async function scanResources(resourceType) {
                try {
                    const button = event.target;
                    const originalText = button.innerHTML;

                    // Show loading state
                    button.innerHTML = '<i data-lucide="loader-2" class="inline h-5 w-5 mr-2 animate-spin"></i>Scanning ' + resourceType + '...';
                    button.disabled = true;
                    lucide.createIcons();

                    const response = await fetch('/api/discover-resources', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            cloudProvider: selectedProvider,
                            clientName: selectedClient
                        })
                    });

                    const data = await response.json();

                    if (data.success) {
                        if (resourceType === 'EC2') {
                            ec2Resources = data.resources.filter(r => r.service_type === 'EC2');
                            displayResources('ec2', ec2Resources);
                            button.innerHTML = '<i data-lucide="check-circle" class="inline h-5 w-5 mr-2"></i>EC2 Scanned (' + ec2Resources.length + ')';
                        } else {
                            rdsResources = data.resources.filter(r => r.service_type === 'RDS');
                            displayResources('rds', rdsResources);
                            button.innerHTML = '<i data-lucide="check-circle" class="inline h-5 w-5 mr-2"></i>RDS Scanned (' + rdsResources.length + ')';
                        }

                        button.classList.add('bg-green-500', 'hover:bg-green-600');
                        button.classList.remove('bg-gradient-to-r', 'from-green-500', 'to-emerald-500', 'hover:from-green-600', 'hover:to-emerald-600');
                    } else {
                        button.innerHTML = originalText;
                    }

                    button.disabled = false;
                    lucide.createIcons();
                } catch (error) {
                    console.error('Error scanning resources:', error);
                    button.innerHTML = originalText;
                    button.disabled = false;
                    lucide.createIcons();
                }
            }

            function displayResources(type, resources) {
                const table = document.getElementById(type + '-table');
                const tbody = document.getElementById(type + '-tbody');

                tbody.innerHTML = '';

                resources.forEach(resource => {
                    const row = document.createElement('div');
                    row.className = 'resource-row px-6 py-4 grid grid-cols-12 gap-4 items-center cursor-pointer';
                    row.onclick = function(e) {
                        // Don't trigger row click if clicking directly on checkbox
                        if (e.target.type !== 'checkbox') {
                            const checkbox = row.querySelector('input[type="checkbox"]');
                            checkbox.checked = !checkbox.checked;
                            updateSelectedResources();
                        }
                    };
                    row.innerHTML = `
                        <div class="col-span-1">
                            <input type="checkbox" value="${resource.service_type}|${resource.id}|${resource.region}" 
                                   onchange="updateSelectedResources()" class="rounded border-gray-300">
                        </div>
                        <div class="col-span-3 font-mono text-sm">${resource.id}</div>
                        <div class="col-span-3">${resource.name}</div>
                        <div class="col-span-2">${resource.type}</div>
                        <div class="col-span-2">
                            <span class="px-3 py-1 rounded-full text-xs font-medium ${getStatusColor(resource.state || resource.status)}">
                                ${resource.state || resource.status}
                            </span>
                        </div>
                        <div class="col-span-1">${resource.region}</div>
                    `;
                    tbody.appendChild(row);
                });

                table.classList.remove('hidden');
            }

            function getStatusColor(status) {
                switch (status?.toLowerCase()) {
                    case 'running': case 'available': return 'bg-green-100 text-green-800';
                    case 'stopped': case 'stopping': return 'bg-red-100 text-red-800';
                    case 'pending': case 'starting': return 'bg-yellow-100 text-yellow-800';
                    default: return 'bg-gray-100 text-gray-800';
                }
            }

            function updateSelectedResources() {
                var checkboxes = document.querySelectorAll('input[type="checkbox"]:checked');
                selectedResources = [];
                for (var i = 0; i < checkboxes.length; i++) {
                    if (checkboxes[i].value.includes('|')) {
                        selectedResources.push(checkboxes[i].value);
                    }
                }
                updateNavigationButtons();
            }

            function toggleSelectAll(type) {
                var selectAll = document.getElementById(type + '-select-all');
                var checkboxes = document.querySelectorAll('#' + type + '-tbody input[type="checkbox"]');

                // Add visual feedback animation to select all checkbox
                selectAll.style.transform = 'scale(1.1)';
                setTimeout(() => {
                    selectAll.style.transform = 'scale(1)';
                }, 200);

                // Animate each individual checkbox
                for (var i = 0; i < checkboxes.length; i++) {
                    checkboxes[i].checked = selectAll.checked;

                    // Add staggered animation effect
                    setTimeout(function(checkbox, index) {
                        return function() {
                            checkbox.style.transform = 'scale(1.2)';
                            checkbox.parentElement.style.background = selectAll.checked ? 
                                'linear-gradient(135deg, rgba(61, 179, 227, 0.1), rgba(232, 101, 160, 0.1))' : '';

                            setTimeout(() => {
                                checkbox.style.transform = 'scale(1)';
                                if (!selectAll.checked) {
                                    checkbox.parentElement.style.background = '';
                                }
                            }, 150);
                        };
                    }(checkboxes[i], i), i * 50);
                }

                // Update selected resources after animations
                setTimeout(() => {
                    updateSelectedResources();
                }, checkboxes.length * 50 + 200);
            }

            function proceedToStep5A() {
                updateNavigationButtons();
            }

            function selectFrequency(frequency) {
                selectedFrequency = frequency;

                // Update UI - Remove selected state from all cards and hide all checkmarks
                document.querySelectorAll('.report-card').forEach(function(card) {
                    card.classList.remove('selected');
                });
                document.querySelectorAll('[id$="-check"]').forEach(function(check) {
                    check.classList.add('hidden');
                });

                // Add selected state to clicked card and show its checkmark
                document.getElementById(frequency + '-card').classList.add('selected');
                document.getElementById(frequency + '-check').classList.remove('hidden');

                // Show download button instead of next button
                document.getElementById('download-utilization-btn').classList.remove('hidden');

                // Hide navigation buttons since we're using download button
                document.getElementById('next-btn').classList.add('hidden');
            }

            async function downloadUtilizationReport() {
                try {
                    const downloadBtn = document.getElementById('download-utilization-btn');
                    const originalText = downloadBtn.innerHTML;

                    // Show loading animation
                    downloadBtn.innerHTML = '<i data-lucide="loader-2" class="inline h-5 w-5 mr-2 animate-spin"></i>Generating Report...';
                    downloadBtn.disabled = true;
                    lucide.createIcons();

                    const currentDate = new Date().toISOString().split('T')[0];
                    const filename = selectedClient + '-' + currentDate + '-utilization-report.pdf';

                    const response = await fetch('/api/generate-report', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            cloudProvider: selectedProvider,
                            clientName: selectedClient,
                            reportType: 'utilization',
                            resources: selectedResources,
                            frequency: selectedFrequency
                        })
                    });

                    if (response.ok) {
                        const blob = await response.blob();
                        const url = window.URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.href = url;
                        a.download = filename;
                        a.click();
                        window.URL.revokeObjectURL(url);

                        // Show success state briefly
                        downloadBtn.innerHTML = '<i data-lucide="check-circle" class="inline h-5 w-5 mr-2"></i>Downloaded Successfully!';
                        downloadBtn.classList.add('bg-green-500', 'hover:bg-green-600');
                        downloadBtn.classList.remove('button-black-bubble');

                        // Reset after 2 seconds
                        setTimeout(() => {
                            downloadBtn.innerHTML = originalText;
                            downloadBtn.classList.remove('bg-green-500', 'hover:bg-green-600');
                            downloadBtn.classList.add('button-black-bubble');
                            downloadBtn.disabled = false;
                            lucide.createIcons();
                        }, 2000);
                    } else {
                        throw new Error('Failed to generate report');
                    }
                } catch (error) {
                    console.error('Error generating report:', error);
                    const downloadBtn = document.getElementById('download-utilization-btn');
                    downloadBtn.innerHTML = '<i data-lucide="alert-circle" class="inline h-5 w-5 mr-2"></i>Error - Try Again';
                    downloadBtn.classList.add('bg-red-500', 'hover:bg-red-600');
                    downloadBtn.classList.remove('button-black-bubble');

                    // Reset after 3 seconds
                    setTimeout(() => {
                        downloadBtn.innerHTML = '<i data-lucide="download" class="inline h-5 w-5 mr-2"></i>Download PDF Report';
                        downloadBtn.classList.remove('bg-red-500', 'hover:bg-red-600');
                        downloadBtn.classList.add('button-black-bubble');
                        downloadBtn.disabled = false;
                        lucide.createIcons();
                    }, 3000);
                }
            }



            function proceedToStep5B() {
                updateNavigationButtons();
            }

            async function showBillingData(month, year, frequency) {
                try {
                    const response = await fetch('/api/get-billing-preview', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            cloudProvider: selectedProvider,
                            clientName: selectedClient,
                            month: parseInt(month),
                            year: parseInt(year),
                            frequency: 'monthly'
                        })
                    });

                    const data = await response.json();

                    if (data.success) {
                        displayBillingDataWithCharts(data.billingData, 'monthly');
                    }
                } catch (error) {
                    console.error('Error fetching billing data:', error);
                    displayErrorMessage();
                }
            }

            function displayBillingDataWithCharts(billingData, frequency) {
                const container = document.getElementById('billing-data-container');

                if (billingData && billingData.services) {
                    let html = `
                        <div class="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
                            <!-- Summary Section -->
                            <div class="billing-summary">
                                <h3 class="text-2xl font-bold text-blue-900 mb-2">Client: ${selectedClient.charAt(0).toUpperCase() + selectedClient.slice(1)}</h3>
                                <h3 class="text-2xl font-bold text-blue-900 mb-4">Cost Summary</h3>
                                <div class="bg-white rounded-lg p-6 shadow-lg">
                                    <div class="text-3xl font-bold text-green-600 mb-2">$${billingData.total_cost.toFixed(2)}</div>
                                    <p class="text-gray-700 mb-2">Period: ${billingData.billing_period}</p>
                                    <p class="text-sm text-gray-600">Frequency: ${frequency.charAt(0).toUpperCase() + frequency.slice(1)}</p>
                                </div>
                            </div>

                            <!-- Pie Chart -->
                            <div class="bg-white rounded-lg p-6 shadow-lg">
                                <h4 class="text-lg font-semibold mb-4 text-center">Cost Distribution</h4>
                                <canvas id="billingPieChart" width="300" height="300"></canvas>
                            </div>
                        </div>



                        <!-- Detailed Table -->
                        <div class="bg-white rounded-xl shadow-lg overflow-hidden">
                            <div class="bg-gray-50 px-6 py-4 border-b">
                                <h4 class="text-lg font-semibold">Service Breakdown</h4>
                            </div>
                            <div class="bg-gray-50 px-6 py-4 border-b">
                                <div class="grid grid-cols-4 gap-4 text-sm font-semibold text-gray-700">
                                    <div>Service</div>
                                    <div>Cost (USD)</div>
                                    <div>Percentage</div>
                                    <div>Trend</div>
                                </div>
                            </div>
                            <div class="divide-y divide-gray-200">
                    `;

                    billingData.services.forEach((service, index) => {
                        const percentage = (service.amount / billingData.total_cost * 100).toFixed(1);
                        const trendIcon = index % 3 === 0 ? '📈' : index % 3 === 1 ? '📉' : '➡️';
                        const trendText = index % 3 === 0 ? 'Up' : index % 3 === 1 ? 'Down' : 'Stable';
                        html += `
                            <div class="px-6 py-4 grid grid-cols-4 gap-4 items-center hover:bg-gray-50">
                                <div class="font-medium">${service.service}</div>
                                <div class="text-lg font-semibold">$${service.amount.toFixed(2)}</div>
                                <div class="text-sm text-gray-600">${percentage}%</div>
                                <div class="text-sm text-gray-600">${trendIcon} ${trendText}</div>
                            </div>
                        `;
                    });

                    html += `
                            </div>
                        </div>
                    `;

                    container.innerHTML = html;

                    // Create charts after DOM is updated
                    setTimeout(function() {
                        createBillingCharts(billingData, frequency);
                    }, 100);

                } else {
                    displayErrorMessage();
                }
            }

            function displayErrorMessage() {
                const container = document.getElementById('billing-data-container');
                container.innerHTML = `
                    <div class="text-center py-12">
                        <i data-lucide="alert-circle" class="h-16 w-16 text-gray-400 mx-auto mb-4"></i>
                        <h3 class="text-lg font-semibold text-gray-900 mb-2">No billing data available</h3>
                        <p class="text-gray-600">No billing data found for the selected period.</p>
                    </div>
                `;
                lucide.createIcons();
            }

            function createBillingCharts(billingData, frequency) {
                // Create Pie Chart
                const pieCtx = document.getElementById('billingPieChart');
                if (pieCtx) {
                    new Chart(pieCtx, {
                        type: 'pie',
                        data: {
                            labels: billingData.services.slice(0, 8).map(s => s.service),
                            datasets: [{
                                data: billingData.services.slice(0, 8).map(s => s.amount),
                                backgroundColor: [
                                    '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', 
                                    '#9966FF', '#FF9F40', '#FF6384', '#C9CBCF'
                                ],
                                borderWidth: 2,
                                borderColor: '#fff'
                            }]
                        },
                        options: {
                            responsive: true,
                            plugins: {
                                legend: {
                                    position: 'bottom',
                                    labels: {
                                        padding: 10,
                                        usePointStyle: true,
                                        font: {
                                            size: 11
                                        }
                                    }
                                }
                            }
                        }
                    });
                }


            }

            async function downloadBillingReport() {
                try {
                    const month = document.getElementById('month-select').value;
                    const year = document.getElementById('year-select').value;
                    const monthName = document.getElementById('month-select').options[document.getElementById('month-select').selectedIndex].text;
                    const filename = selectedClient + '-billing-' + monthName + '-' + year + '.pdf';

                    const response = await fetch('/api/generate-report', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            cloudProvider: selectedProvider,
                            clientName: selectedClient,
                            reportType: 'billing',
                            month: parseInt(month),
                            year: parseInt(year),
                            frequency: 'monthly'
                        })
                    });

                    if (response.ok) {
                        const blob = await response.blob();
                        const url = window.URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.href = url;
                        a.download = filename;
                        a.click();
                        window.URL.revokeObjectURL(url);
                    }
                } catch (error) {
                    console.error('Error generating billing report:', error);
                }
            }

            // Initialize
            document.addEventListener('DOMContentLoaded', function() {
                updateStepIndicator();
                lucide.createIcons();
            });
        </script>
    </body>
    </html>
    '''


@app.route('/api/nubinix-clients', methods=['GET'])
def get_nubinix_clients_api():
    """Get list of Nubinix clients from organization SSM."""
    try:
        logger.info("Fetching Nubinix clients from organization SSM")
        clients = get_nubinix_clients()

        logger.info(f"Found {len(clients)} clients: {clients}")
        return jsonify({'success': True, 'clients': clients})

    except Exception as e:
        logger.error(f"Error fetching Nubinix clients: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Failed to fetch clients: {str(e)}'
        }), 500


@app.route('/api/discover-resources', methods=['POST'])
def discover_resources_api():
    """Discover resources for the selected cloud provider and client."""
    try:
        data = request.get_json()
        cloud_provider = data.get('cloudProvider')
        client_name = data.get('clientName')

        if not cloud_provider or not client_name:
            return jsonify({
                'success':
                False,
                'error':
                'Cloud provider and client name are required'
            }), 400

        logger.info(
            f"Discovering {cloud_provider} resources for client: {client_name}"
        )

        if cloud_provider == 'AWS':
            # Get credentials for the client from SSM
            credentials = get_credentials_for_client(client_name)
            if not credentials:
                return jsonify({
                    'success':
                    False,
                    'error':
                    f'Failed to get credentials for client: {client_name}'
                }), 500

            # Discover AWS resources
            resources = discover_aws_resources(credentials['access_key'],
                                               credentials['secret_key'])

        elif cloud_provider == 'Azure':
            # For Azure, we would need different credential handling
            # This is a placeholder for Azure implementation
            resources = []
            logger.warning("Azure resource discovery not yet implemented")

        else:
            return jsonify({
                'success':
                False,
                'error':
                f'Unsupported cloud provider: {cloud_provider}'
            }), 400

        logger.info(f"Discovered {len(resources)} resources")
        return jsonify({'success': True, 'resources': resources})

    except Exception as e:
        logger.error(f"Error discovering resources: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Failed to discover resources: {str(e)}'
        }), 500


@app.route('/api/generate-report', methods=['POST'])
def generate_report_api():
    """Generate and return a PDF report."""
    try:
        data = request.get_json()
        cloud_provider = data.get('cloudProvider')
        client_name = data.get('clientName')
        report_type = data.get('reportType')
        resources = data.get('resources', [])
        frequency = data.get('frequency', 'daily')
        month = data.get('month')
        year = data.get('year')

        # Validate required fields
        if not all([cloud_provider, client_name, report_type]):
            return jsonify({
                'success':
                False,
                'error':
                'Missing required fields: cloudProvider, clientName, reportType'
            }), 400

        # For utilization reports, resources are required
        if report_type == 'utilization' and not resources:
            return jsonify({
                'success':
                False,
                'error':
                'Resources are required for utilization reports'
            }), 400

        # Limit resources for weekly reports to prevent timeout
        if frequency == 'weekly' and len(resources) > 15:
            logger.warning(f"Limiting weekly report to 15 resources (out of {len(resources)})")
            resources = resources[:15]

        logger.info(
            f"Generating {report_type} report for {cloud_provider} client {client_name} with {len(resources)} resources"
        )

        if cloud_provider == 'AWS':
            # Get credentials for the client
            credentials = get_credentials_for_client(client_name)
            if not credentials:
                return jsonify({
                    'success':
                    False,
                    'error':
                    f'Failed to get credentials for client: {client_name}'
                }), 500

            # Generate the report
            if report_type == 'billing':
                # For billing reports, we need month and year
                if not month or not year:
                    month = datetime.now().month
                    year = datetime.now().year

            pdf_data = generate_comprehensive_report(
                client_name=client_name,
                cloud_provider=cloud_provider,
                report_type=report_type,
                credentials=credentials,
                resources=resources,
                frequency=frequency)

        else:
            return jsonify({
                'success':
                False,
                'error':
                f'Report generation not implemented for {cloud_provider}'
            }), 400

        # Create temporary file for the PDF
        temp_fd, temp_path = tempfile.mkstemp(suffix='.pdf')
        os.close(temp_fd)

        with open(temp_path, 'wb') as f:
            f.write(pdf_data)

        # Generate filename based on report type
        if report_type == 'utilization':
            current_date = datetime.now().strftime('%Y-%m-%d')
            filename = f"{client_name}-{current_date}-utilization-report.pdf"
        else:  # billing report
            if not month or not year:
                month = datetime.now().month
                year = datetime.now().year
            filename = f"{client_name}-{client_name}-{month:02d}-{year}-billing-report.pdf"

        logger.info(f"Report generated successfully: {filename}")
        
        # Schedule automatic cleanup after 5 minutes
        schedule_post_report_cleanup()
        logger.info("Scheduled automatic cleanup in 5 minutes to remove client details and sensitive data")

        return send_file(temp_path,
                         mimetype='application/pdf',
                         as_attachment=True,
                         download_name=filename)

    except Exception as e:
        logger.error(f"Error generating report: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Failed to generate report: {str(e)}'
        }), 500


@app.route('/api/get-billing-preview', methods=['POST'])
def get_billing_preview():
    """Get billing data preview for display."""
    try:
        data = request.get_json()
        cloud_provider = data.get('cloudProvider')
        client_name = data.get('clientName')
        month = data.get('month')
        year = data.get('year')
        frequency = data.get('frequency', 'daily')

        if not all([cloud_provider, client_name, month, year]):
            return jsonify({
                'success': False,
                'error': 'Missing required parameters'
            }), 400

        logger.info(
            f"Getting {frequency} billing data for {client_name} - {month}/{year}"
        )

        if cloud_provider == 'AWS':
            # Get credentials for the client
            credentials = get_credentials_for_client(client_name)
            if not credentials:
                return jsonify({
                    'success':
                    False,
                    'error':
                    f'Failed to get credentials for client: {client_name}'
                }), 500

            # Convert credentials to expected format
            billing_creds = {
                'accessKeyId': credentials['access_key'],
                'secretAccessKey': credentials['secret_key']
            }

            # Get billing data with frequency consideration
            billing_data = get_client_billing_data(billing_creds, month, year,
                                                   frequency)

            return jsonify({'success': True, 'billingData': billing_data})
        else:
            return jsonify({
                'success':
                False,
                'error':
                f'Billing preview not implemented for {cloud_provider}'
            }), 400

    except Exception as e:
        logger.error(f"Error getting billing preview: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Failed to get billing preview: {str(e)}'
        }), 500


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint with cleanup service status."""
    return jsonify({
        'status': 'healthy',
        'service': 'Nubinix Cloud Insights',
        'cleanup_service': 'active',
        'auto_cleanup_delay': '5 minutes after report generation',
        'timestamp': datetime.now().isoformat()
    })


@app.route('/api/force-cleanup', methods=['POST'])
def force_cleanup():
    """Force immediate cleanup of sensitive data."""
    try:
        force_immediate_cleanup()
        return jsonify({
            'success': True,
            'message': 'Cleanup completed successfully'
        })
    except Exception as e:
        logger.error(f"Error during forced cleanup: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Cleanup failed: {str(e)}'
        }), 500



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
