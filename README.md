# **Crypto Trading Bot** 🚀

A cryptocurrency trading bot designed for the **HK Web3 Quant Trading Hackathon**, utilizing the **Roostoo Mock Exchange API**. This bot is a work in progress and aims to implement fully autonomous trading strategies.

---

## **Features**
- Connects to the **Roostoo Mock Exchange API** for fetching real-time market data.
- Modular structure for future strategy and risk management implementations.
- Built with Python and designed for easy extension.

---

## **Setup Instructions**

### **1. Clone the Repository**
```bash
git clone https://github.com/Jackyman666/crypto-trading-bot.git
cd crypto-trading-bot
```

### **2. Create and Activate a Virtual Environment**
```bash
python -m venv venv
```

- **Activate**:
  - **Windows**: `venv\Scripts\activate`
  - **macOS/Linux**: `source venv/bin/activate`

### **3. Install Dependencies**
```bash
pip install -r requirements.txt
```

### **4. Set Up Environment Variables**
Create a `.env` file in the root directory with the following content:
```plaintext
ROOSTOO_BASE_URL=https://mock-api.roostoo.com
ROOSTOO_API_KEY=your_roostoo_api_key
ROOSTOO_SECRET_KEY=your_roostoo_secret_key
```

Replace the placeholders with your actual API credentials.

---

## **How to Run**
1. **Activate the Virtual Environment**:
   ```bash
   source venv/bin/activate  # macOS/Linux
   venv\Scripts\activate     # Windows
   ```

2. **Run the Bot**:
   ```bash
   python main.py
   ```

---

## **Next Steps**
- Implement trading strategies (e.g., Moving Average Crossover, Mean Reversion).
- Add risk management modules.
- Include backtesting functionality.
- Deploy to AWS EC2 for 24/7 operation.
