import yfinance as yf
import streamlit as st
import datetime as dt

#Title
st.title("first indicators project")
st.text("First project importing data from yahoo finance and showing it in graphas and such stuff")

Company = st.text_input("Enter the company ticker")
com = yf.Ticker(Company)

#info
info = com.info

#st.text(json.dumps(info, indent=2))


for key, value in info.items():
    st.text(f"{key}: {value}")


#History 


st.header("history")

starter = st.text_input("enter start date in format YYYY-MM-DD")
ender = st.text_input("enter end date in format YYYY-MM-DD")
Start_date = dt.datetime.strptime(starter, "%Y-%m-%d")
end_date = dt.datetime.strptime(ender, "%Y-%m-%d")
history = com.history(start= Start_date, end = end_date)
st.table(history)

#visualize


#history[Close].plot(title = f"{Company} sStock Price from {starter} to {ender}")
st.title(f"Visualizing {Company} from {starter} to {ender}")

see_what = st.text_input("what do you want to see, choose one: Open, High, Low, Close, Volume, Dividends, Stock Splits")

st.header(f"{see_what}")

st.area_chart(data = history[see_what], x_label="Date", y_label="Price", color="#ff0000", use_container_width=True)


