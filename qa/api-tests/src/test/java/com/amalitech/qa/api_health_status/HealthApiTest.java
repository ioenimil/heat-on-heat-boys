package com.amalitech.qa.api_health_status;

import io.restassured.RestAssured;
import io.restassured.http.ContentType;
import org.testng.annotations.BeforeClass;
import org.testng.annotations.Test;

import static io.restassured.RestAssured.*;
import static org.hamcrest.Matchers.*;

public class HealthApiTest {

    @BeforeClass
    public void setup() {
        RestAssured.baseURI = "http://localhost:8080";
    }

//    Testing to confirm if the health endpoint returns 200 status code
    @Test
    public void testHealthEndpointReturnsHttp200() {
        given()
                .contentType(ContentType.JSON)
                .when()
                .get("/api/health")
                .then()
                .statusCode(200);
    }

    //    Testing to confirm if the health endpoint returns OK as the response message when status code is 200
    @Test
    public void testHealthEndpointReturnsMessageOK() {
        given()
                .contentType(ContentType.JSON)
                .when()
                .get("/api/health")
                .then()
                .statusCode(200)
                .body("message", equalTo("OK"));
    }


}