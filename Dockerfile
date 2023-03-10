# Use the Python base image
FROM --platform=linux/amd64 python:3.10-alpine

# Set a working directory
WORKDIR /app

# Copy all requirements
COPY requirements* .

# Install any dependencies of the function
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy all the files from the local directory into the container
COPY . .

# Run the function
ENTRYPOINT [ "python", "update-linear-action.py" ]