import uvicorn

def main():
    uvicorn.run("api.app:app", host="0.0.0.0", port=8101, debug=True, reload=True)

if __name__ == "__main__":
    main()
